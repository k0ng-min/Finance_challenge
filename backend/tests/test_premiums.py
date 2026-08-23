from datetime import date

from app.models.kb import Insurer, InsurerPremium
from app.routers.insurers import _attach_published_premiums, get_premium_comparison


def _seed_premium(db_session, premium: int = 10_000) -> None:
    insurer = Insurer(name="테스트보험", code="TEST")
    db_session.add(insurer)
    db_session.flush()
    db_session.add(InsurerPremium(
        insurer_id=insurer.insurer_id,
        sex="M",
        age=30,
        plan_name="표준",
        is_standard_tier=True,
        premium=premium,
        period_days=7,
        product_name="테스트 해외여행보험",
        basis="보험기간 7일 / 표준보장 담보 기준",
        source="보험다모아",
        source_url="https://example.test/premiums",
        collected_at=date(2026, 8, 2),
    ))
    db_session.commit()


def test_published_premium_is_not_scaled_by_requested_trip_days(db_session):
    _seed_premium(db_session)

    results = [
        get_premium_comparison(age=30, sex="M", days=days, db=db_session)
        for days in (3, 7, 14)
    ]

    assert [r.items[0].published_premium for r in results] == [10_000, 10_000, 10_000]
    assert [r.premium_period_days for r in results] == [1, 1, 1]
    assert all("premium_total" not in r.model_dump() for r in results)


def test_ranking_receives_only_published_premium_and_metadata(db_session):
    _seed_premium(db_session)
    ranking = [{"insurer_code": "TEST"}]

    _attach_published_premiums(db_session, ranking, age=30, sex="M")

    item = ranking[0]
    assert item["published_premium"] == 10_000
    assert item["premium_period_days"] == 1
    assert item["premium_basis"] == "보험기간 1일 / 표준보장 담보 기준"
    assert item["premium_source"] == "보험다모아"
    assert "premium_total" not in item
    assert "premium_days" not in item


def test_가격표_등급명이_등급_매핑과_어긋나지_않는다():
    """가격 시트의 등급명과 실속/표준/고급 매핑이 어긋나면, 등급으로 가격을 못 찾아
    그 보험사만 조용히 값이 안 뜬다. 실제로 메리츠가 "보장이 큰 플랜"(띄어쓰기)과
    "보장이큰플랜" 사이에서 이렇게 어긋날 뻔했다."""
    from app.seed_premiums_actual import _PLAN_NAME_ALIASES, _SHEET_CONFIG
    from app.services.insurer_tiers import TIER_PLAN_NAMES

    for code, _vertical, standard_plan in _SHEET_CONFIG.values():
        known = set(TIER_PLAN_NAMES[code])
        aliased = set(_PLAN_NAME_ALIASES.get(code, {}).values())
        assert aliased <= known, f"{code}: 별칭이 등급 매핑에 없는 이름을 가리킨다 — {aliased - known}"
        assert standard_plan in known, f"{code}: 대표 등급 {standard_plan}이 등급 매핑에 없다"


def test_메리츠는_실속_표준만_있고_고급_등급이_없다():
    """메리츠가 실제로 파는 건 실속플랜과 보장이큰플랜 둘뿐이다. 보장이큰플랜을 표준에
    두고, 고급 자리는 비운다 — 없는 등급을 있는 척 매핑하면 다른 보험사의 고급과
    나란히 놓고 비교하게 된다."""
    from app.services.insurer_tiers import plan_name_for_tier

    assert plan_name_for_tier("MERITZ", 0) == "실속플랜"
    assert plan_name_for_tier("MERITZ", 1) == "보장이큰플랜"
    assert plan_name_for_tier("MERITZ", 2) is None


def test_그_등급_상품이_없는_보험사는_순위에서_뺀다():
    """자료가 없는 게 아니라 상품 자체가 없다. 남겨두면 다른 축 점수만으로 순위가
    매겨져서, 팔지도 않는 등급의 보험사가 목록에 끼어든다."""
    from app.routers.insurers import _drop_insurers_without_plan

    ranking = [
        {"insurer_code": "KB", "insurer_name": "KB손해보험"},
        {"insurer_code": "MERITZ", "insurer_name": "메리츠화재"},
    ]

    kept, dropped = _drop_insurers_without_plan(ranking, plan_tier=2)
    assert [r["insurer_code"] for r in kept] == ["KB"]
    assert dropped == ["메리츠화재"]

    kept, dropped = _drop_insurers_without_plan(ranking, plan_tier=1)
    assert len(kept) == 2 and dropped == []
