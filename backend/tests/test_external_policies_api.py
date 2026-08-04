"""라우터를 실제로 호출해 검증한다 — registry 단위 테스트만으로는 권한 로직이 안 잡힌다."""
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.user import AppUser


@pytest.fixture
def client(db_session):
    """앱의 DB 의존성을 테스트 세션으로 바꿔 끼운다 — 운영 DB를 건드리지 않기 위해."""
    db_session.add(AppUser(user_id=1, nickname="테스트", auth_provider="guest"))
    db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_사용가능한_수집방식에_codef는_빠져있다(client):
    res = client.get("/users/1/external-policies/providers")
    assert res.status_code == 200
    names = [p["name"] for p in res.json()]
    assert "manual" in names
    assert "mock" in names
    assert "codef" not in names


def test_수동입력_실손은_세대까지_저장된다(client):
    res = client.post("/users/1/external-policies/link", json={
        "provider": "manual",
        "items": [{"kind": "MEDICAL_INDEMNITY", "insurer_name_raw": "삼성화재", "enrolled_ym": "2019-05"}],
    })
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["indemnity_gen"] == 3
    assert body[0]["source"] == "manual"

    listed = client.get("/users/1/external-policies").json()
    assert len(listed) == 1


def test_게스트는_로그인필요_provider를_쓸_수_없다(client):
    """mock은 requires_login=True다. 토큰 없이 부르면 401이어야 한다."""
    res = client.post("/users/1/external-policies/link", json={"provider": "mock", "items": []})
    assert res.status_code == 401


def test_알수없는_보험종류는_400으로_거부한다(client):
    res = client.post("/users/1/external-policies/link", json={
        "provider": "manual", "items": [{"kind": "NOT_A_KIND"}],
    })
    assert res.status_code == 400


def test_등록한_기존보험을_삭제할_수_있다(client):
    created = client.post("/users/1/external-policies/link", json={
        "provider": "manual", "items": [{"kind": "ACCIDENT"}],
    }).json()
    policy_id = created[0]["external_policy_id"]

    assert client.delete(f"/users/1/external-policies/{policy_id}").status_code == 200
    assert client.get("/users/1/external-policies").json() == []


def test_여행자보험이_없으면_진단은_빈_결과다(client):
    res = client.get("/users/1/coverage-overlap")
    assert res.status_code == 200
    body = res.json()
    assert body == {"duplicates": [], "gaps": [], "fixed_ok": [], "unknown": []}
