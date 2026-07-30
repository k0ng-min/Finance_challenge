import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.user import AppUser, Trip
from app.models.analysis import AnalysisRun
from app.routers.auth import get_current_user_optional, verify_owner
from app.schemas import TripCreate, RecommendationOut
from app.services.rules import build_risk_profile, generate_pre_trip_findings
from app.services.finding_persistence import persist_findings, load_findings_out
from app.services.deletion import delete_trip_cascade

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=RecommendationOut)
@limiter.limit("20/minute")
def create_trip_and_recommend(
    request: Request, payload: TripCreate, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    verify_owner(payload.user_id, current)
    user = db.get(AppUser, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다. 먼저 /users로 사용자를 생성하세요.")

    risk_profile = build_risk_profile(
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        purpose=payload.purpose,
        activities=payload.activities,
        companion_type=payload.companion_type,
        rental_car=payload.rental_car,
    )
    # coverage_priority는 build_risk_profile()이 만드는 값이 아니라 사용자가 직접 고른 값이라,
    # 위험도 판단과는 분리해서 별도로 risk_profile에 얹는다(보험사 순위 매길 때 그대로 재사용).
    risk_profile["coverage_priority"] = payload.coverage_priority

    trip = Trip(
        user_id=payload.user_id,
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        purpose=payload.purpose,
        activities=json.dumps(payload.activities, ensure_ascii=False),
        companion_type=payload.companion_type,
        rental_car=payload.rental_car,
        risk_profile=json.dumps(risk_profile, ensure_ascii=False, default=str),
        coverage_priority=json.dumps(payload.coverage_priority, ensure_ascii=False),
    )
    db.add(trip)
    db.flush()

    finding_specs = generate_pre_trip_findings(db, risk_profile)

    run = AnalysisRun(
        user_id=payload.user_id,
        run_type="가입전추천",
        trip_id=trip.trip_id,
        result_summary=json.dumps({"finding_count": len(finding_specs)}, ensure_ascii=False),
    )
    db.add(run)
    db.flush()

    findings_out = persist_findings(db, run, finding_specs)
    db.commit()

    return RecommendationOut(
        analysis_run_id=run.analysis_run_id,
        trip_id=trip.trip_id,
        risk_profile=risk_profile,
        findings=findings_out,
    )


@router.get("/{trip_id}", response_model=RecommendationOut)
def get_trip_recommendation(
    trip_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """규칙엔진을 재실행하지 않고 마지막 추천 결과를 그대로 조회한다 (페이지 재방문/새로고침용)."""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="여행 정보를 찾을 수 없습니다.")
    verify_owner(trip.user_id, current)
    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.trip_id == trip_id)
        .order_by(AnalysisRun.analysis_run_id.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="아직 추천 결과가 없습니다.")
    return RecommendationOut(
        analysis_run_id=run.analysis_run_id,
        trip_id=trip.trip_id,
        risk_profile=json.loads(trip.risk_profile) if trip.risk_profile else {},
        findings=load_findings_out(db, run.analysis_run_id),
    )


@router.delete("/{trip_id}")
def delete_trip(
    trip_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="여행 정보를 찾을 수 없습니다.")
    verify_owner(trip.user_id, current)
    delete_trip_cascade(db, trip)
    db.commit()
    return {"status": "deleted"}
