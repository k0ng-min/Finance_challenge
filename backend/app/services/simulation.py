"""사고 시뮬레이션 — "이 여행에서 이런 일이 나면 보험사별로 어떻게 갈리는가".

지금까지 보험사 비교는 전부 표의 숫자(보험료·지급한도)였다. 사용자는 숫자 차이를
체감하지 못한다. 여기서는 **기존 청구 판정 엔진을 그대로 태워서** 같은 사고에 대해
보험사별 결론이 조항 원문과 함께 갈리는 것을 보여준다.

새로 만든 것은 조회 범위 하나뿐이다. claim_review.relevant_coverages_for_type()은
사용자가 등록한 담보(user_coverage)를 기준으로 도는데, 가입 전에는 등록된 담보가 없다.
그래서 policy_version 전체 담보를 도는 자매 함수를 두되, **판정 로직(rank_maps —
직접/조건부/면책 순서와 활동 수식자 기반 면책 우선)은 손대지 않고 그대로 호출한다.**
두 화면의 판정 기준이 갈라지면 어느 쪽이 맞는지 설명할 수 없게 된다.

경계:
- 근거 조항이 없는 보험사는 조용히 빼지 않고 "확인불가"로 남긴다. 빠지면 "그 보험사가
  더 나은가?"로 오독된다(보험료 비교의 unavailable_insurers와 같은 원칙).
- L2 세분화는 사용자가 고른 값만 쓴다. 시뮬레이션에는 자유서술이 없어 L2를 추론할
  근거가 없으므로 추측하지 않는다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product,
    SimulationScenario,
)
from app.models.user import Trip
from app.services.claim_review import rank_maps
from app.services.clause_quote import quote_clause
from app.services.travel_alert import CLAUSE_FROM_LEVEL, country_alert

UNKNOWN = "확인불가"

#: 화면에 한 번에 보여줄 시나리오 수. 더 늘리면 보험사 6개 × 시나리오로 표가 금방 커진다.
MAX_SCENARIOS = 4


@dataclass
class SimulationResult:
    insurer_name: str
    verdict: str                       # 직접 | 조건부 | 면책 | 확인불가
    coverage_name: str | None = None
    clause_article_no: str | None = None
    clause_quote: str | None = None


@dataclass
class SimulatedScenario:
    code: str
    title: str
    narrative: str
    l1_type_id: int
    selected_type_id: int
    incident_type_name: str
    sub_types: list[dict] = field(default_factory=list)
    results: list[SimulationResult] = field(default_factory=list)


def _activities(trip: Trip) -> str:
    """여행에 적힌 활동 + 목적을 한 문자열로. rules._has_risky_activity와 같은 방식으로
    부분 문자열을 찾는다 — 활동 입력이 자유 텍스트라 정확 일치로는 못 잡는다."""
    parts: list[str] = []
    if trip.activities:
        try:
            parts.extend(json.loads(trip.activities))
        except (json.JSONDecodeError, TypeError):
            parts.append(str(trip.activities))
    if trip.purpose:
        parts.append(trip.purpose)
    return " ".join(str(p) for p in parts)


def _has_nationwide_alert(db: Session, destination: str | None) -> bool:
    """그 나라 **일반 지역** 단계가 3단계 이상인가.

    지역 경보(일본의 후쿠시마, 필리핀의 민다나오)로는 발동하지 않는다. 국가 최고 단계로
    판정하면 도쿄 여행자에게 소요 시나리오가 뜨고, 그러면 사용자는 경보 자체를 무시하게
    된다(services/travel_alert.py의 같은 경계).
    """
    alert = country_alert(db, destination)
    return bool(alert and alert.baseline and alert.baseline.level >= CLAUSE_FROM_LEVEL)


def select_scenarios(db: Session, trip: Trip) -> list[SimulationScenario]:
    """여행 정보로 시나리오를 고른다. 조건은 전부 행에 적혀 있으므로 여기 분기가 늘지 않는다."""
    rows = db.query(SimulationScenario).order_by(SimulationScenario.sort_order).all()
    joined_activities = _activities(trip)
    nationwide = None  # 필요할 때만 조회한다(경보 조회는 DB를 한 번 더 탄다)

    picked: list[SimulationScenario] = []
    risky_taken = False
    for row in rows:
        if row.require_activity:
            # 위험활동은 최대 1건만 — '등반'이 '전문등반'의 부분 문자열이라 둘이 함께 걸린다.
            if risky_taken or row.require_activity not in joined_activities:
                continue
            risky_taken = True
        if row.require_rental_car and not trip.rental_car:
            continue
        if row.require_alert_nationwide:
            if nationwide is None:
                nationwide = _has_nationwide_alert(db, trip.destination)
            if not nationwide:
                continue
        picked.append(row)
        if len(picked) >= MAX_SCENARIOS:
            break
    return picked


def expand_type_ids(db: Session, type_id: int) -> list[int]:
    """조회에 쓸 사고유형 id 목록.

    조항 매핑(clause_incident_map)은 **L2에만** 걸려 있다. 그래서 L1 시나리오를 그대로
    조회하면 전 보험사가 "확인불가"로 나온다 — 근거가 없어서가 아니라 조회 축이 어긋나서다.
    L1이면 그 아래 L2 전체로 넓히고, L2면 그 하나만 본다.
    """
    children = [
        row[0] for row in
        db.query(IncidentType.type_id).filter(IncidentType.parent_id == type_id).all()
    ]
    return [type_id] + children


def simulate_coverages_for_type(
    db: Session, type_ids: list[int], policy_version_id: int, modifiers: dict | None = None,
) -> list[tuple[Coverage, ClauseIncidentMap]]:
    """그 약관(policy_version) 전체 담보 중 이 사고유형에 매핑된 조항을 가진 것들을,
    claim_review와 **같은 순서**로 정렬해서 돌려준다.

    user_coverage를 타지 않는다는 점만 relevant_coverages_for_type과 다르다.
    """
    if not type_ids:
        return []
    maps = (
        db.query(ClauseIncidentMap)
        .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
        .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
        .filter(
            ClauseIncidentMap.type_id.in_(type_ids),
            Coverage.policy_version_id == policy_version_id,
        )
        .all()
    )
    if not maps:
        return []
    ranked = rank_maps(maps, modifiers)
    return [(m.clause.coverage, m) for m in ranked if m.clause and m.clause.coverage]


def _results_for_type(
    db: Session, type_id: int, modifiers: dict | None,
) -> list[SimulationResult]:
    """보험사마다 대표 판정 한 줄. 근거가 없으면 확인불가로 남긴다."""
    type_ids = expand_type_ids(db, type_id)
    rows = (
        db.query(Insurer, PolicyVersion.policy_version_id)
        .join(Product, Product.insurer_id == Insurer.insurer_id)
        .join(PolicyVersion, PolicyVersion.product_id == Product.product_id)
        .order_by(Insurer.code)
        .all()
    )
    results: list[SimulationResult] = []
    for insurer, pv_id in rows:
        ranked = simulate_coverages_for_type(db, type_ids, pv_id, modifiers)
        if not ranked:
            results.append(SimulationResult(insurer_name=insurer.name, verdict=UNKNOWN))
            continue
        coverage, best = ranked[0]
        results.append(SimulationResult(
            insurer_name=insurer.name,
            verdict=best.relevance,
            coverage_name=coverage.raw_name,
            clause_article_no=best.clause.article_no,
            clause_quote=quote_clause(best.clause, _anchor(best, modifiers)),
        ))
    return results


def _anchor(best: ClauseIncidentMap, modifiers: dict | None) -> str | None:
    """인용문을 어디에서 잘라낼지 정하는 기준 문구.

    면책 판정이 활동 수식자 때문에 올라온 것이면(예: "스쿠버다이빙"), 그 문구가 인용문
    안에 반드시 들어가야 한다. 면책 조항은 열거 항목이 길어서 앞에서부터 200자를 자르면
    정작 근거가 된 문구가 통째로 잘려나가고, "인용은 있는데 근거는 없는" 상태가 된다.
    """
    activity = (modifiers or {}).get("activity")
    if not activity or best.relevance != "면책" or not best.clause or not best.clause.text:
        return None
    return activity if activity in best.clause.text else None


def _sub_types(db: Session, l1_type_id: int) -> list[dict]:
    rows = (
        db.query(IncidentType)
        .filter(IncidentType.parent_id == l1_type_id, IncidentType.is_active.is_(True))
        .order_by(IncidentType.type_id)
        .all()
    )
    return [{"type_id": t.type_id, "name": t.name} for t in rows]


def build_one_scenario(
    db: Session, trip: Trip, code: str, type_id: int | None = None,
) -> SimulatedScenario:
    """시나리오 하나만 다시 계산한다.

    칩(세분화 선택)을 하나 눌렀다고 다른 3개 시나리오까지 전 보험사분 조회를
    새로 돌 이유가 없다 — build_simulation()은 화면 최초 진입 때만 쓰고,
    이후 칩 클릭은 이 함수로 바뀐 시나리오 하나만 다시 태운다. 시나리오가
    이 여행에 실제로 뜬 것인지는 select_scenarios()로 다시 확인한다 —
    그래야 다른 여행/다른 조건에서만 뜨는 시나리오 코드를 끼워 넣어 엉뚱한
    결과를 만들 수 없다.
    """
    scenario = next((s for s in select_scenarios(db, trip) if s.code == code), None)
    if scenario is None:
        raise ValueError(f"'{code}' 시나리오는 이 여행에 해당하지 않습니다.")

    modifiers = json.loads(scenario.modifiers) if scenario.modifiers else None
    sub_types = _sub_types(db, scenario.type_id)

    resolved_type_id = scenario.type_id
    if type_id is not None:
        if not any(s["type_id"] == type_id for s in sub_types):
            raise ValueError(f"'{code}' 시나리오에 속하지 않는 사고유형입니다.")
        resolved_type_id = type_id

    type_row = db.get(IncidentType, resolved_type_id)
    return SimulatedScenario(
        code=scenario.code,
        title=scenario.title,
        narrative=scenario.narrative,
        l1_type_id=scenario.type_id,
        selected_type_id=resolved_type_id,
        incident_type_name=type_row.name if type_row else "",
        sub_types=sub_types,
        results=_results_for_type(db, resolved_type_id, modifiers),
    )


def build_simulation(
    db: Session, trip: Trip, selected: dict[str, int] | None = None,
) -> list[SimulatedScenario]:
    """시나리오별 × 보험사별 결과.

    `selected`는 {시나리오 code: 사용자가 고른 L2 type_id}. 그 L2가 정말 이 시나리오
    L1의 자식일 때만 받아들이고, 아니면 ValueError를 던진다 — 다른 L1의 L2를 끼워 넣어
    엉뚱한 판정을 만들지 못하게 한다(호출부가 400으로 바꾼다).
    """
    selected = selected or {}
    out: list[SimulatedScenario] = []

    for scenario in select_scenarios(db, trip):
        modifiers = json.loads(scenario.modifiers) if scenario.modifiers else None
        sub_types = _sub_types(db, scenario.type_id)

        type_id = scenario.type_id
        chosen = selected.get(scenario.code)
        if chosen is not None:
            if not any(s["type_id"] == chosen for s in sub_types):
                raise ValueError(f"'{scenario.code}' 시나리오에 속하지 않는 사고유형입니다.")
            type_id = chosen

        type_row = db.get(IncidentType, type_id)
        out.append(SimulatedScenario(
            code=scenario.code,
            title=scenario.title,
            narrative=scenario.narrative,
            l1_type_id=scenario.type_id,
            selected_type_id=type_id,
            incident_type_name=type_row.name if type_row else "",
            sub_types=sub_types,
            results=_results_for_type(db, type_id, modifiers),
        ))
    return out
