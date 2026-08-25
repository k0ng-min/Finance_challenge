"""약관 조항 검색(/clauses/search) — 실제 약관 KB가 있어야 의미가 있는 테스트.

예전에는 `app.main`을 import하면 앱이 전역 engine으로 운영 DB(data/app.db)를 직접 열었기
때문에, 이 파일은 그 파일이 존재하는지만 확인하고 TestClient를 그대로 썼다. 이제 테스트는
운영 DB를 아예 열지 않으므로(conftest 참고) 다른 테스트들과 같은 방법을 쓴다 — `kb_session`
픽스처가 운영 DB를 **사본으로** 떠서 주고, 그 세션을 get_db에 끼운다. 검사 내용은 그대로다.
"""
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


@pytest.fixture
def client(kb_session):
    app.dependency_overrides[get_db] = lambda: kb_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_검색어가_2자_미만이면_400(client):
    r = client.get("/clauses/search?insurer_code=SAMSUNG&keyword=제")
    assert r.status_code == 400


def test_없는_보험사면_404(client):
    r = client.get("/clauses/search?insurer_code=NOPE&keyword=제4조")
    assert r.status_code == 404


def test_조항번호로_검색하면_원문과_사고유형_매핑이_함께_온다(client):
    r = client.get("/clauses/search?insurer_code=SAMSUNG&keyword=제4조")
    assert r.status_code == 200
    results = r.json()
    if not results:
        pytest.skip("약관 KB에 SAMSUNG 약관이 아직 시드되지 않았습니다")

    for item in results:
        assert "제4조" in item["clause"]["article_no"] or "제4조" in item["clause"]["text"]
        for link in item["incident_links"]:
            assert link["relevance"] in ("직접", "조건부", "면책", "제한")
