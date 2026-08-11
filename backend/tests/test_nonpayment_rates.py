import os

import pytest

_APP_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")


def test_시드는_스냅샷이_없으면_아무일도_하지_않는다(db_session, tmp_path):
    from app.seed_nonpayment_rates import seed

    missing_path = tmp_path / "does-not-exist.json"
    assert seed(db_session, path=missing_path) == 0


def test_scope_note는_여행자보험_단독_수치가_아님을_밝힌다():
    """전체 보험종목 기준 공시라는 사실을 화면에서도 감추지 않는다 — 스냅샷 자체에
    고정해 둔다."""
    import json
    from pathlib import Path

    snapshot = Path(__file__).resolve().parents[1] / "data" / "nonpayment_rates.json"
    if not snapshot.exists():
        pytest.skip("nonpayment_rates.json 스냅샷이 없습니다")
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert "여행자보험" in payload["scope_note"]
    assert "순위 점수에는 넣지 않는다" in payload["scope_note"]


def test_6개사가_모두_매칭됐다():
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 건너뜁니다")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.kb import Insurer, NonpaymentRate

    engine = create_engine(f"sqlite:///{_APP_DB_PATH}")
    db = sessionmaker(bind=engine)()
    try:
        rows = db.query(NonpaymentRate).filter(NonpaymentRate.insurer_id.isnot(None)).all()
        if not rows:
            pytest.skip("운영 DB에 nonpayment_rate가 아직 시드되지 않았습니다")
        matched_codes = {db.get(Insurer, r.insurer_id).code for r in rows}
        expected = {"SAMSUNG", "HYUNDAI", "MERITZ", "KB", "DB", "KAKAOPAY"}
        assert matched_codes == expected
        for r in rows:
            assert 0 <= r.unpaid_rate <= 100
    finally:
        db.close()
