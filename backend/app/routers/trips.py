import json
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.user import AppUser, Trip, UserPolicy
from app.models.analysis import AnalysisRun
from app.routers.auth import get_current_user_optional, verify_owner
from app.models.kb import FlightDelayStat
from app.schemas import (
    TripCreate, TripUpdate, TripDetailOut, RecommendationOut, FlightDelayStatOut,
    FlightDelayStatsOut, OnsitePackOut, SimulationOut, SimulatedScenarioOut,
)
from app.services.rules import build_risk_profile, generate_pre_trip_findings
from app.services.travel_alert import build_alert_findings, country_alert
from app.services.finding_persistence import persist_findings, load_findings_out
from app.services.deletion import delete_trip_cascade, wipe_user_data
from app.services.onsite import build_onsite_pack
from app.services.simulation import build_simulation, build_one_scenario

#: 시뮬레이션 화면에 고정으로 붙는 경계 문구. 서버가 내려보내 화면과 테스트가 같은 문장을
#: 쓴다 — 이 기능은 약관 조항 매핑을 보여줄 뿐 지급을 약속하지 않는다.
SIMULATION_DISCLAIMER = (
    "이 결과는 각 보험사 약관 조항의 사고유형 매핑에 근거한 예시입니다. "
    "실제 보험금 지급 여부는 사고 경위와 보험사 심사에 따라 달라질 수 있으니, "
    "가입 전에 해당 보험사에 직접 확인하세요."
)

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
        raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없어요. 페이지를 새로고침한 뒤 다시 시도해 주세요.")
    if payload.end_date <= payload.start_date:
        raise HTTPException(status_code=400, detail="종료일은 시작일 다음 날 이후여야 합니다.")

    # 게스트(비로그인)는 여행 1개 + 거기 이어지는 보험 1개 + 사고 1개만 들고 간다. 새 여행을
    # 등록하면 앞의 기록(사고 포함)은 정리한다 — 로그인 계정만 여러 건을 쌓아둘 수 있다.
    if current is None:
        wipe_user_data(db, payload.user_id)

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
    # 목적지 여행경보. 지금까지 risk_level은 활동과 여행일수만 봤기 때문에, 시리아에 가든
    # 일본에 가든 "관광"이면 똑같이 낮음이 나왔다. 경보는 외교부 자료라 약관 근거와 출처가
    # 다르므로, 같은 risk_level에 섞지 않고 별도 항목으로 둔다(보험사 순위 점수에도 넣지 않는다).
    # 경보는 지역 단위라 '그 나라 일반 지역 단계(baseline)'와 '지역별 경보(regions)'를 나눠
    # 담는다. 최고 단계를 나라 대표로 쓰면 일본이 3단계(후쿠시마 30km), 필리핀이 4단계
    # (민다나오 일부)가 되어 도쿄·세부 여행자에게 출국권고가 뜬다.
    alert = country_alert(db, payload.destination)
    risk_profile["travel_alert"] = alert.as_dict() if alert else None
    if alert:
        # 사용자가 실제로 체크한 지역만 남긴다 — 화면에서 "어느 지역 때문에 이 안내가
        # 붙었는지"를 되짚을 수 있어야 한다.
        chosen = set(payload.visiting_alert_region_ids)
        risk_profile["travel_alert"]["visiting_regions"] = [
            r.as_dict() for r in alert.alerting_regions() if r.alert_id in chosen
        ]

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
    # 경보가 높은 곳으로 가면 그 보험사 약관의 전쟁·내란 면책 조항을 원문과 함께 덧붙인다.
    # 경보 자체를 보상 판정 근거로 쓰지는 않는다(services/travel_alert.py 참고).
    finding_specs += build_alert_findings(
        db, payload.destination, payload.visiting_alert_region_ids,
    )

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


@router.get("/travel-alerts/{country}")
@limiter.limit("60/minute")
def get_travel_alert(request: Request, country: str, db: Session = Depends(get_db)):
    """목적지의 여행경보. 여행 준비 STEP 1에서 나라를 고르는 즉시 조회한다.

    외교부가 공개한 자료라 로그인 없이 볼 수 있게 둔다 — 가입 전 단계라 계정이 없는
    사용자도 지나가는 화면이다.

    자료에 없는 나라면 `alert: null`. "정보 없음"조차 화면에 띄우지 않는다 — 대부분의
    안전한 나라가 여기 해당해서 매번 빈 줄이 생긴다.
    """
    alert = country_alert(db, country)
    return {"alert": alert.as_dict() if alert else None}


@router.get("/flight-delay-stats", response_model=FlightDelayStatsOut)
def get_flight_delay_stats(db: Session = Depends(get_db)):
    """한국공항공사 실제 항공지연 통계(전체기간 합산). 약관의 지연기준시간(예: "4시간
    이상 지연")을 체감 가능한 크기와 나란히 보여주는 데 쓴다 — 지연 발생 확률이 아니라
    평균 지연시간·건수 같은 크기 비교까지만 제공한다(FlightDelayStat 모델 docstring 참고)."""
    rows = db.query(FlightDelayStat).filter(FlightDelayStat.year.is_(None)).all()
    if not rows:
        raise HTTPException(status_code=404, detail="항공지연 통계가 아직 적재되지 않았습니다.")
    first = rows[0]
    return FlightDelayStatsOut(
        source=first.source, source_url=first.source_url,
        coverage_period="2017-01 ~ 2025-05", scope_note=first.scope_note,
        collected_at=first.collected_at,
        overall=[FlightDelayStatOut.model_validate(r) for r in rows],
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


@router.get("/{trip_id}/detail", response_model=TripDetailOut)
def get_trip_detail(
    trip_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """여행 수정 화면이 현재 값을 채워 넣기 위해 쓰는 조회 — 추천 결과 없이 기본 정보만 준다."""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="여행 정보를 찾을 수 없습니다.")
    verify_owner(trip.user_id, current)
    insurer_name = None
    if trip.user_policy_id:
        policy = db.get(UserPolicy, trip.user_policy_id)
        if policy:
            insurer_name = policy.insurer_name_raw
    return TripDetailOut(
        trip_id=trip.trip_id, destination=trip.destination,
        start_date=trip.start_date, end_date=trip.end_date,
        purpose=trip.purpose, companion_type=trip.companion_type,
        user_policy_id=trip.user_policy_id, insurer_name=insurer_name,
    )


@router.patch("/{trip_id}", response_model=TripDetailOut)
def update_trip(
    trip_id: int, payload: TripUpdate, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """사고 접수 중에 목적지·기간만 급히 넣어 만든 여행을 나중에 제대로 고칠 수 있게 한다.
    추천 결과(AnalysisRun)는 다시 계산하지 않는다 — 여행 정보 자체만 바로잡는 용도다."""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="여행 정보를 찾을 수 없습니다.")
    verify_owner(trip.user_id, current)

    start = payload.start_date if payload.start_date is not None else trip.start_date
    end = payload.end_date if payload.end_date is not None else trip.end_date
    if start and end and end <= start:
        raise HTTPException(status_code=400, detail="종료일은 시작일 다음 날 이후여야 합니다.")

    for field in ("destination", "start_date", "end_date", "purpose", "companion_type"):
        value = getattr(payload, field)
        if value is not None:
            setattr(trip, field, value)
    db.commit()

    insurer_name = None
    if trip.user_policy_id:
        policy = db.get(UserPolicy, trip.user_policy_id)
        if policy:
            insurer_name = policy.insurer_name_raw
    return TripDetailOut(
        trip_id=trip.trip_id, destination=trip.destination,
        start_date=trip.start_date, end_date=trip.end_date,
        purpose=trip.purpose, companion_type=trip.companion_type,
        user_policy_id=trip.user_policy_id, insurer_name=insurer_name,
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


@router.get("/{trip_id}/onsite", response_model=OnsitePackOut)
@limiter.limit("30/minute")
def get_trip_onsite_pack(
    request: Request, trip_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """이 여행 기준 현지 대응 팩.

    여행에 보험이 연결돼 있으면 그 보험사 요건만, 아니면 전 보험사 합집합을 보여준다
    (요건마다 어느 보험사 조항인지는 응답에 함께 담긴다).
    """
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="여행 정보를 찾을 수 없습니다.")
    verify_owner(trip.user_id, current)
    pack = build_onsite_pack(db, country=trip.destination, trip=trip)
    return OnsitePackOut(**asdict(pack))


@router.get("/{trip_id}/simulation", response_model=SimulationOut)
@limiter.limit("30/minute")
def get_trip_simulation(
    request: Request, trip_id: int,
    select: list[str] = Query(default_factory=list),
    db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """이 여행에서 일어날 수 있는 사고를 보험사별로 미리 돌려본다.

    `select`는 "시나리오코드:L2사고유형id" 형태를 여러 번 받는다(예:
    `?select=THEFT:12&select=ILLNESS:7`). 세분화를 고르지 않으면 L1 기준으로 계산한다.
    그 L2가 해당 시나리오 L1의 자식이 아니면 400으로 거절한다 — 다른 L1의 L2를 끼워 넣어
    엉뚱한 판정을 만들지 못하게 한다.
    """
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="여행 정보를 찾을 수 없습니다.")
    verify_owner(trip.user_id, current)

    selected: dict[str, int] = {}
    for item in select:
        code, _, raw_type_id = item.partition(":")
        if not code or not raw_type_id.isdigit():
            raise HTTPException(status_code=400, detail="사고유형 선택값을 다시 확인해 주세요.")
        selected[code] = int(raw_type_id)

    try:
        scenarios = build_simulation(db, trip, selected)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SimulationOut(
        trip_id=trip.trip_id,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        scenarios=[asdict(s) for s in scenarios],
        disclaimer=SIMULATION_DISCLAIMER,
    )


@router.get("/{trip_id}/simulation/{code}", response_model=SimulatedScenarioOut)
@limiter.limit("60/minute")
def get_trip_simulation_scenario(
    request: Request, trip_id: int, code: str,
    type_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """시나리오 하나만 다시 계산한다(칩으로 세분화를 바꿨을 때).

    화면에서 세분화 칩 하나를 누르면 이 엔드포인트만 부른다 — 나머지 시나리오
    3개까지 전 보험사분 다시 조회하던 것을, 바뀐 시나리오 하나로 줄인다.
    """
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="여행 정보를 찾을 수 없습니다.")
    verify_owner(trip.user_id, current)

    try:
        scenario = build_one_scenario(db, trip, code, type_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SimulatedScenarioOut(**asdict(scenario))
