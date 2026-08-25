import os

import pytest

_APP_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")


def test_검색어가_2자_미만이면_400():
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 건너뜁니다")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.get("/clauses/search?insurer_code=SAMSUNG&keyword=제")
    assert r.status_code == 400


def test_없는_보험사면_404():
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 건너뜁니다")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.get("/clauses/search?insurer_code=NOPE&keyword=제4조")
    assert r.status_code == 404


def test_조항번호로_검색하면_원문과_사고유형_매핑이_함께_온다():
    """운영 DB가 없는 환경(CI 등)에서는 건너뛴다."""
    if not os.path.exists(_APP_DB_PATH):
        pytest.skip("운영 DB(backend/data/app.db)가 없어 건너뜁니다")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.get("/clauses/search?insurer_code=SAMSUNG&keyword=제4조")
    assert r.status_code == 200
    results = r.json()
    if not results:
        pytest.skip("운영 DB에 SAMSUNG 약관이 아직 시드되지 않았습니다")

    for item in results:
        assert "제4조" in item["clause"]["article_no"] or "제4조" in item["clause"]["text"]
        for link in item["incident_links"]:
            assert link["relevance"] in ("직접", "조건부", "면책", "제한")
