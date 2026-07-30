from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import AppUser, UserPolicy, UserCoverage
from app.models.kb import Coverage
from app.routers.auth import get_current_user, get_current_user_optional, verify_owner
from app.schemas import UserPolicyCreate, UserPolicyOut, UserCoverageOut
from app.services.policy_matching import match_insurer, match_product_and_version

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
            match_confidence=1.0 if uc.coverage_id else 0.0,
        ))
    return UserPolicyOut(
        user_policy_id=policy.user_policy_id,
        insurer_name_raw=policy.insurer_name_raw,
        product_name_raw=policy.product_name_raw,
        subscriber_age=policy.subscriber_age,
        period_start=policy.period_start,
        period_end=policy.period_end,
        matched_insurer_code=policy.product.insurer.code if policy.product else None,
        matched_insurer_name=policy.product.insurer.name if policy.product else None,
        matched_product_name=policy.product.name if policy.product else None,
        coverages=coverages_out,
    )


def create_policy_for_user(
    db: Session, *, user_id: int, insurer_name_raw: str, product_name_raw: str | None = None,
    subscriber_age: int | None = None, period_start, period_end,
) -> UserPolicy:
    """보험 등록의 실제 로직 — 담보는 사용자가 직접 고르지 않고, 매칭된 상품이 실제로
    파는 담보 목록(Coverage 테이블, 실제 약관 기준)을 그대로 채워 넣는다. 자기신고 방식
    체크리스트보다 신뢰할 수 있고, 사용자가 담보를 하나하나 고르는 수고도 없앤다.
    incidents.py에서 게스트가 사고 접수 시 보험사만 고른 경우에도 이 함수를 그대로 재사용한다."""
    insurer = match_insurer(db, insurer_name_raw)
    product, policy_version = (None, None)
    if insurer:
        product, policy_version = match_product_and_version(db, insurer, product_name_raw or "")

    policy = UserPolicy(
        user_id=user_id,
        product_id=product.product_id if product else None,
        policy_version_id=policy_version.policy_version_id if policy_version else None,
        insurer_name_raw=insurer_name_raw,
        product_name_raw=product_name_raw,
        subscriber_age=subscriber_age,
        period_start=period_start,
        period_end=period_end,
    )
    db.add(policy)
    db.flush()

    if policy_version:
        real_coverages = (
            db.query(Coverage).filter(Coverage.policy_version_id == policy_version.policy_version_id).all()
        )
        for cov in real_coverages:
            db.add(UserCoverage(
                user_policy_id=policy.user_policy_id,
                coverage_id=cov.coverage_id,
                coverage_std_id=cov.coverage_std_id,
                raw_name=cov.raw_name,
                subscribed_amount=cov.limit_amount,
            ))

    db.commit()
    db.refresh(policy)
    return policy


@router.post("", response_model=UserPolicyOut)
def register_policy(
    user_id: int, payload: UserPolicyCreate, db: Session = Depends(get_db),
    current: AppUser = Depends(get_current_user),
):
    """보험 등록·관리는 로그인 계정에서만 한다 — 게스트는 데이터가 기기/브라우저에 묶여 있어
    "내 보험"처럼 여러 번 다시 찾아와 관리하는 기능과는 맞지 않는다."""
    verify_owner(user_id, current)
    user = db.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    policy = create_policy_for_user(
        db, user_id=user_id, insurer_name_raw=payload.insurer_name_raw,
        product_name_raw=payload.product_name_raw, subscriber_age=payload.subscriber_age,
        period_start=payload.period_start, period_end=payload.period_end,
    )
    return _to_out(policy)


@router.get("", response_model=list[UserPolicyOut])
def list_policies(
    user_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    # 조회는 게스트도 허용한다 — 사고 접수 화면(guest 경로)이 방금 자동 등록한 보험을
    # 바로 이어서 써야 하기 때문. 다만 verify_owner가 남의 user_id는 여전히 막는다.
    verify_owner(user_id, current)
    user = db.get(AppUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    policies = db.query(UserPolicy).filter(UserPolicy.user_id == user_id).all()
    return [_to_out(p) for p in policies]


@router.delete("/{policy_id}")
def delete_policy(
    user_id: int, policy_id: int, db: Session = Depends(get_db),
    current: AppUser = Depends(get_current_user),
):
    verify_owner(user_id, current)
    policy = db.get(UserPolicy, policy_id)
    if not policy or policy.user_id != user_id:
        raise HTTPException(status_code=404, detail="보험 정보를 찾을 수 없습니다.")
    db.query(UserCoverage).filter(UserCoverage.user_policy_id == policy_id).delete()
    db.delete(policy)
    db.commit()
    return {"status": "deleted"}
