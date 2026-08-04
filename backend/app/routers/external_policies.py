"""기존보험 등록·조회와 중복보장 진단 API."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.external import ExternalCoverage, ExternalPolicy
from app.models.kb import Coverage, CoverageStd
from app.models.user import AppUser, Trip, UserPolicy
from app.routers.auth import get_current_user_optional, verify_owner
from app.schemas import (
    ExternalPolicyLinkRequest, ExternalPolicyOut, OverlapReportOut, ProviderOut,
)
from app.services.coverage_overlap import diagnose
from app.services.external_policy.registry import get_provider, list_available_providers

router = APIRouter(prefix="/users/{user_id}/external-policies", tags=["external-policies"])


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(user_id: int):
    """프론트는 이 목록으로 버튼을 그린다 — CODEF가 꺼져 있으면 버튼 자체가 안 보인다."""
    return [ProviderOut(name=p.name, requires_login=p.requires_login)
            for p in list_available_providers()]


@router.get("", response_model=list[ExternalPolicyOut])
def list_external_policies(
    user_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    verify_owner(user_id, current)
    return db.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).all()


@router.post("/link", response_model=list[ExternalPolicyOut])
def link_external_policies(
    user_id: int, payload: ExternalPolicyLinkRequest, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """등록 진입점 하나로 모든 수집 방식을 받는다 — 방식이 늘어도 라우터는 바뀌지 않는다."""
    verify_owner(user_id, current)
    if not db.get(AppUser, user_id):
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    try:
        provider = get_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    available = {p.name for p in list_available_providers()}
    if provider.name not in available:
        raise HTTPException(status_code=400, detail=f"'{provider.name}' 연동은 아직 사용할 수 없습니다.")

    # 외부 인증이 필요한 방식은 로그인 계정에서만 — 게스트는 자격증명을 안전하게 보관할 곳이 없다.
    if provider.requires_login and (current is None or current.auth_provider == "guest"):
        raise HTTPException(status_code=401, detail="이 연동은 로그인 후 이용할 수 있습니다.")

    credentials = {"items": [i.model_dump() for i in payload.items]}
    try:
        dtos = provider.fetch(user=current, credentials=credentials)
    except NotImplementedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    created = []
    for dto in dtos:
        policy = ExternalPolicy(
            user_id=user_id, source=dto.source, kind=dto.kind,
            insurer_name_raw=dto.insurer_name_raw, product_name_raw=dto.product_name_raw,
            enrolled_ym=dto.enrolled_ym, indemnity_gen=dto.indemnity_gen,
            raw_payload=json.dumps(dto.raw_payload, ensure_ascii=False) if dto.raw_payload else None,
        )
        db.add(policy)
        db.flush()
        for cov in dto.coverages:
            std = (
                db.query(CoverageStd)
                .filter(CoverageStd.std_code == cov.coverage_std_code).first()
                if cov.coverage_std_code else None
            )
            db.add(ExternalCoverage(
                external_policy_id=policy.external_policy_id,
                coverage_std_id=std.coverage_std_id if std else None,
                raw_name=cov.raw_name, subscribed_amount=cov.subscribed_amount,
                amount_source=cov.amount_source,
            ))
        created.append(policy)

    db.commit()
    for p in created:
        db.refresh(p)
    return created


@router.delete("/{external_policy_id}")
def delete_external_policy(
    user_id: int, external_policy_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    verify_owner(user_id, current)
    policy = db.get(ExternalPolicy, external_policy_id)
    if not policy or policy.user_id != user_id:
        raise HTTPException(status_code=404, detail="기존보험 정보를 찾을 수 없습니다.")
    db.delete(policy)
    db.commit()
    return {"status": "deleted"}


overlap_router = APIRouter(prefix="/users/{user_id}", tags=["external-policies"])


@overlap_router.get("/coverage-overlap", response_model=OverlapReportOut)
def coverage_overlap(
    user_id: int,
    trip_id: int | None = Query(default=None),
    user_policy_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """검토 대상 담보는 등록된 여행자보험에서 가져온다. trip_id를 주면 그 여행에 묶인 보험을 쓴다."""
    verify_owner(user_id, current)

    if user_policy_id is None and trip_id is not None:
        trip = db.get(Trip, trip_id)
        if trip and trip.user_id == user_id:
            user_policy_id = trip.user_policy_id

    target_ids: list[int] = []
    if user_policy_id is not None:
        policy = db.get(UserPolicy, user_policy_id)
        if policy and policy.user_id == user_id and policy.policy_version_id:
            target_ids = [
                c.coverage_std_id
                for c in db.query(Coverage)
                .filter(Coverage.policy_version_id == policy.policy_version_id).all()
                if c.coverage_std_id
            ]

    external = db.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).all()
    report = diagnose(db, external_policies=external, target_coverage_std_ids=sorted(set(target_ids)))
    return OverlapReportOut(
        duplicates=[f.__dict__ for f in report.duplicates],
        gaps=[f.__dict__ for f in report.gaps],
        fixed_ok=[f.__dict__ for f in report.fixed_ok],
        unknown=[f.__dict__ for f in report.unknown],
    )
