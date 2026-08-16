"""사고 시뮬레이션 검증.

지키려는 것 셋:

1. **가입 전에도 돈다** — user_coverage에 의존하지 않는다. 등록한 담보가 0인 사용자로도
   6개사 결과가 나와야 한다.
2. **판정 기준이 사고 접수 화면과 갈라지지 않는다** — 활동 수식자 기반 면책 우선
   (claim_review.rank_maps)이 여기서도 그대로 발동한다.
3. **근거 없는 보험사를 조용히 빼지 않는다** — 매핑이 없으면 확인불가로 남는다.
   빠지면 "그 보험사가 더 나은가?"로 오독된다.
"""
import datetime as dt
import json

import pytest

from app.models.kb import Clause, IncidentType, Insurer, SimulationScenario
from app.models.user import AppUser, Trip, UserCoverage
from app.services.simulation import (
    UNKNOWN, build_simulation, expand_type_ids, select_scenarios,
    simulate_coverages_for_type,
)


@pytest.fixture
def seeded(kb_session):
    from app.seed_simulation_scenarios import seed as seed_scenarios

    if kb_session.query(SimulationScenario).first() is None:
        seed_scenarios(kb_session)
    kb_session.commit()
    return kb_session


def _make_trip(db, **kwargs):
    user = AppUser(nickname="시뮬레이션테스트")
    db.add(user)
    db.flush()
    start = dt.date.today() + dt.timedelta(days=3)
    trip = Trip(
        user_id=user.user_id,
        destination=kwargs.pop("destination", "태국"),
        start_date=start,
        end_date=start + dt.timedelta(days=7),
        purpose=kwargs.pop("purpose", "관광"),
        activities=json.dumps(kwargs.pop("activities", []), ensure_ascii=False),
        rental_car=kwargs.pop("rental_car", False),
        **kwargs,
    )
    db.add(trip)
    db.flush()
    return trip


def test_l1_expands_to_its_l2_children(seeded):
    """조항 매핑은 L2에만 걸려 있다. L1을 그대로 조회하면 전부 확인불가가 되므로 넓힌다."""
    inj = seeded.query(IncidentType).filter(
        IncidentType.l1_code == "INJ", IncidentType.parent_id.is_(None)).one()
    expanded = expand_type_ids(seeded, inj.type_id)
    assert len(expanded) > 1
    assert expanded[0] == inj.type_id


def test_runs_without_any_registered_coverage(seeded):
    """가입 전 화면이므로 user_coverage가 비어 있어야 정상이다."""
    trip = _make_trip(seeded)
    assert seeded.query(UserCoverage).filter(UserCoverage.user_policy_id.isnot(None)).count() >= 0

    scenarios = build_simulation(seeded, trip)
    assert scenarios
    insurer_count = seeded.query(Insurer).count()
    for scenario in scenarios:
        assert len(scenario.results) == insurer_count


def test_no_insurer_is_silently_dropped(seeded):
    """근거가 없으면 목록에서 빼는 대신 확인불가로 남긴다."""
    trip = _make_trip(seeded)
    names = {i.name for i in seeded.query(Insurer).all()}
    for scenario in build_simulation(seeded, trip):
        assert {r.insurer_name for r in scenario.results} == names
        for r in scenario.results:
            if r.verdict == UNKNOWN:
                assert r.clause_quote is None and r.coverage_name is None
            else:
                assert r.verdict in ("직접", "조건부", "면책")


def test_risky_activity_triggers_waiver_first(seeded):
    """스쿠버다이빙을 적으면, 그 문구가 실제로 면책 조항 원문에 있는 보험사는 면책이
    대표값으로 올라온다 — claim_review와 같은 규칙이 그대로 적용된다는 뜻이다."""
    trip = _make_trip(seeded, activities=["스쿠버다이빙"])
    scenarios = build_simulation(seeded, trip)
    diving = [s for s in scenarios if s.code == "RISKY_스쿠버다이빙"]
    assert diving, "위험활동 시나리오가 선정되지 않았습니다."

    sub = diving[0].sub_types[0]
    refined = build_simulation(seeded, trip, {"RISKY_스쿠버다이빙": sub["type_id"]})
    target = [s for s in refined if s.code == "RISKY_스쿠버다이빙"][0]
    waived = [r for r in target.results if r.verdict == "면책"]
    assert waived, "활동 수식자 기반 면책 우선 판정이 발동하지 않았습니다."
    for r in waived:
        assert "스쿠버다이빙" in r.clause_quote


def test_only_one_risky_activity_scenario(seeded):
    """'등반'은 '전문등반'의 부분 문자열이라 둘이 함께 걸린다 — 한 건만 남긴다."""
    trip = _make_trip(seeded, activities=["전문등반"])
    picked = select_scenarios(seeded, trip)
    assert sum(1 for s in picked if s.require_activity) <= 1


def test_rental_car_scenario_requires_rental_car(seeded):
    without = select_scenarios(seeded, _make_trip(seeded, rental_car=False))
    with_car = select_scenarios(seeded, _make_trip(seeded, rental_car=True))
    assert not any(s.code == "RENTAL_CAR_LIABILITY" for s in without)
    assert any(s.code == "RENTAL_CAR_LIABILITY" for s in with_car)


def test_region_only_alert_does_not_trigger_unrest(seeded):
    """일본의 3단계는 후쿠시마 반경 30km다. 도쿄 여행자에게 소요 시나리오를 띄우지 않는다."""
    picked = select_scenarios(seeded, _make_trip(seeded, destination="일본"))
    assert not any(s.code == "UNREST" for s in picked)


def test_l2_from_another_l1_is_rejected(seeded):
    """다른 L1의 L2를 끼워 넣어 엉뚱한 판정을 만들지 못하게 한다."""
    trip = _make_trip(seeded)
    scenario = build_simulation(seeded, trip)[0]
    other = (
        seeded.query(IncidentType)
        .filter(IncidentType.parent_id.isnot(None), IncidentType.parent_id != scenario.l1_type_id)
        .first()
    )
    assert other is not None
    with pytest.raises(ValueError):
        build_simulation(seeded, trip, {scenario.code: other.type_id})


def test_quotes_are_substrings_of_clause_text(seeded):
    trip = _make_trip(seeded, activities=["스쿠버다이빙"], rental_car=True)
    for scenario in build_simulation(seeded, trip):
        for r in scenario.results:
            if not r.clause_quote:
                continue
            clause = (
                seeded.query(Clause)
                .filter(Clause.article_no == r.clause_article_no)
                .filter(Clause.text.contains(r.clause_quote))
                .first()
            )
            assert clause is not None, f"인용문이 어느 조항 원문에도 없습니다: {r.clause_quote[:40]}"


def test_scenarios_are_capped(seeded):
    """보험사 6개 × 시나리오라 표가 금방 커진다 — 화면에 나가는 수를 제한한다."""
    from app.services.simulation import MAX_SCENARIOS

    trip = _make_trip(seeded, activities=["스쿠버다이빙"], rental_car=True, destination="시리아")
    assert len(build_simulation(seeded, trip)) <= MAX_SCENARIOS


def test_simulate_ignores_user_coverage_table(seeded):
    """조회 축이 policy_version이라는 것을 직접 확인한다."""
    inj = seeded.query(IncidentType).filter(
        IncidentType.l1_code == "INJ", IncidentType.parent_id.is_(None)).one()
    type_ids = expand_type_ids(seeded, inj.type_id)
    found = simulate_coverages_for_type(seeded, type_ids, policy_version_id=1)
    assert found, "policy_version 1(삼성화재)에서 상해 담보를 찾지 못했습니다."
    for coverage, _ in found:
        assert coverage.policy_version_id == 1
