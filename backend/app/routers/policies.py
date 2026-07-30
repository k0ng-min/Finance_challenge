from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import AppUser, UserPolicy, UserCoverage
from app.models.kb import Coverage, CoverageStd
from app.routers.auth import get_current_user_optional, verify_owner
from app.schemas import UserPolicyCreate, UserPolicyOut, UserCoverageOut
from app.services.nlu import get_nlu_engine
from app.services.policy_matching import match_insurer, match_product_and_version, match_coverage

router = APIRouter(prefix="/users/{user_id}/policies", tags=["policies"])


def _to_out(policy: UserPolicy) -> UserPolicyOut:
    coverages_out = []
    for uc in policy.coverages:
        std_name = uc.coverage_std.std_name if uc.coverage_std else None
        std_code = uc.coverage_std.std_code if uc.coverage_std else None
        coverages_out.append(UserCoverageOut(
            user_coverage_id=uc.user_coverage_id,
            raw_name=uc.raw_name,
            subscribed_amount=uc.subscribed_amount,
            matched_std_code=std_code,
            matched_std_name=std_name,
            match_confidence=0.0,  # 호출부(POST/GET)에서 실제 값으로 덮어씀 (ERD에 저장 컬럼 없음)
        ))
    return UserPolicyOut(
        user_policy_id=policy.user_policy_id,
        insurer_name_raw=policy.insurer_name_raw,
        product_name_raw=policy.product_name_raw,
        policy_type=policy.policy_type,
        period_start=policy.period_start,
        period_end=policy.period_end,
        matched_insurer_code=policy.product.insurer.code if policy.product else None,
        matched_insurer_name=policy.product.insurer.name if policy.product else None,
        matched_product_name=policy.product.name if policy.product else None,
        coverages=coverages_out,
    )


@router.post("", response_model=UserPolicyOut)
def register_policy(
    user_id: int, payload: UserPolicyCreate, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    verify_owner(user_id, current)
    user = db.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    nlu = get_nlu_engine()
    insurer = match_insurer(db, payload.insurer_name_raw)
    product, policy_version = (None, None)
    if insurer:
        product, policy_version = match_product_and_version(db, insurer, payload.product_name_raw or "")

    policy = UserPolicy(
        user_id=user_id,
        product_id=product.product_id if product else None,
        policy_version_id=policy_version.policy_version_id if policy_version else None,
        insurer_name_raw=payload.insurer_name_raw,
        product_name_raw=payload.product_name_raw,
        policy_type=payload.policy_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    db.add(policy)
    db.flush()

    # match_confidence는 ERD에 없는 필드라 DB에는 저장하지 않고, 응답 편의를 위해 인메모리로만 들고 있는다.
    confidences: dict[int, float] = {}
    for cov_in in payload.coverages:
        if cov_in.coverage_id is not None:
            # 실제 담보 체크리스트에서 고른 경우 — 퍼지 매칭 없이 그대로 연결한다(신뢰도 100%).
            picked = db.get(Coverage, cov_in.coverage_id)
            coverage_id = picked.coverage_id if picked else None
            coverage_std_id = picked.coverage_std_id if picked else None
            confidence = 1.0 if picked else 0.0
        else:
            coverage_id, coverage_std_id, confidence = match_coverage(db, nlu, cov_in.raw_name, policy_version)
        uc = UserCoverage(
            user_policy_id=policy.user_policy_id,
            coverage_id=coverage_id,
            coverage_std_id=coverage_std_id,
            raw_name=cov_in.raw_name,
            subscribed_amount=cov_in.subscribed_amount,
        )
        db.add(uc)
        db.flush()
        confidences[uc.user_coverage_id] = confidence

    db.commit()
    db.refresh(policy)

    out = _to_out(policy)
    for c in out.coverages:
        c.match_confidence = confidences.get(c.user_coverage_id, 0.0)
    return out


@router.get("", response_model=list[UserPolicyOut])
def list_policies(
    user_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    verify_owner(user_id, current)
    user = db.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    policies = db.query(UserPolicy).filter(UserPolicy.user_id == user_id).all()
    results = []
    for p in policies:
        out = _to_out(p)
        for c_out, uc in zip(out.coverages, p.coverages):
            std = db.get(CoverageStd, uc.coverage_std_id) if uc.coverage_std_id else None
            c_out.match_confidence = 1.0 if uc.coverage_id else (0.6 if std else 0.0)
        results.append(out)
    return results
