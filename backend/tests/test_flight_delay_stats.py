import os

import pytest

_APP_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")


def test_시드는_스냅샷이_없으면_아무일도_하지_않는다(db_session, tmp_path):
    from app.seed_flight_delay_stats import seed

    missing_path = tmp_path / "does-not-exist.json"
    assert seed(db_session, path=missing_path) == 0


def test_scope_note는_확률을_주장하지_않는다():
    """총 운항편수가 원본에 없어 발생 확률을 계산할 근거가 없다 — 이 문구가 화면에도
    그대로 나가므로 스냅샷 자체에서 확률 주장이 없는지 고정해 둔다."""
    import json
    from pathlib import Path

    snapshot = Path(__file__).resolve().parents[1] / "data" / "flight_delay_stats.json"
    if not snapshot.exists():
        pytest.skip("flight_delay_stats.json 스냅샷이 없습니다")
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert "확률" in payload["scope_note"]
    assert "계산할 수 없다" in payload["scope_note"]


def test_국제선_출도착_평균지연시간이_합리적인_범위다():
    """운영 DB가 없는 환경(CI 등)에서는 건너뛴다."""
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 건너뜁니다")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.kb import FlightDelayStat

    engine = create_engine(f"sqlite:///{_APP_DB_PATH}")
    db = sessionmaker(bind=engine)()
    try:
        rows = db.query(FlightDelayStat).filter(
            FlightDelayStat.year.is_(None), FlightDelayStat.kind == "국제"
        ).all()
        if not rows:
            pytest.skip("운영 DB에 flight_delay_stat이 아직 시드되지 않았습니다")
        for row in rows:
            assert row.delayed_flights > 0
            # 평균 지연시간이 몇 분~몇 시간 단위의 합리적인 범위인지만 느슨하게 확인한다
            # (원본 데이터가 바뀌어도 이 테스트가 깨지지 않도록 넓게 잡는다).
            assert 0 < row.avg_delay_minutes < 600
    finally:
        db.close()
