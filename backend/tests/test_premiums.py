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
