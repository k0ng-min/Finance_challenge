"""라우터를 실제로 호출해 검증한다 — registry 단위 테스트만으로는 권한 로직이 안 잡힌다."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.user import AppUser
from app.services.auth import utc_now, hash_session_token


# 소유권 검사가 토큰을 요구하므로(익명 접근 차단) 테스트도 본인 토큰을 들고 부른다.
AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture
def client(db_session):
    """앱의 DB 의존성을 테스트 세션으로 바꿔 끼운다 — 운영 DB를 건드리지 않기 위해."""
    db_session.add(AppUser(
        user_id=1, nickname="테스트", auth_provider="guest",
        session_token=hash_session_token("test-token"),
        session_expires_at=utc_now() + timedelta(days=1),
    ))
    db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_배포_기본값으로는_직접입력만_보인다(client):
    """예전에는 mock도 함께 내려줬다. 고정된 예시(삼성화재 실손 등)를 돌려주는 시연용인데
    배포 기본값에 들어 있어서, 화면에 뜬 예시가 실제 조회 결과처럼 보일 수 있었다.
    codef는 fetch()가 비어 있는 자리표시자라 예전부터 빠져 있었고 그대로 둔다."""
    res = client.get("/users/1/external-policies/providers")
    assert res.status_code == 200
    names = [p["name"] for p in res.json()]
    assert names == ["manual"], f"배포 기본값에 없어야 할 방식이 보입니다: {names}"


def test_시연용_방식은_시연용이라고_함께_알려준다(client, monkeypatch):
    """mock을 켜는 것 자체는 시연에 필요하다. 켜더라도 실제 조회와 구분되지 않으면
    안 되므로, 목록에 그 사실이 함께 실려 내려가야 한다."""
    from app import config

    monkeypatch.setattr(config, "EXTERNAL_POLICY_PROVIDERS", ["manual", "mock"])
    res = client.get("/users/1/external-policies/providers")
    assert res.status_code == 200

    by_name = {p["name"]: p for p in res.json()}
    assert set(by_name) == {"manual", "mock"}
    assert by_name["manual"].get("is_demo") is False
    assert by_name["mock"].get("is_demo") is True
    assert by_name["mock"].get("notice"), "시연용인데 안내 문구가 비어 있습니다"


def test_수동입력_실손은_세대까지_저장된다(client):
    res = client.post("/users/1/external-policies/link", headers=AUTH, json={
        "provider": "manual",
        "items": [{"kind": "MEDICAL_INDEMNITY", "insurer_name_raw": "삼성화재", "enrolled_ym": "2019-05"}],
    })
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["indemnity_gen"] == 3
    assert body[0]["source"] == "manual"

    listed = client.get("/users/1/external-policies", headers=AUTH).json()
    assert len(listed) == 1


def test_게스트는_로그인필요_provider를_쓸_수_없다(client):
    """mock은 requires_login=True다. 토큰 없이 부르면 401이어야 한다."""
    res = client.post("/users/1/external-policies/link", json={"provider": "mock", "items": []})
    assert res.status_code == 401


def test_알수없는_보험종류는_400으로_거부한다(client):
    res = client.post("/users/1/external-policies/link", headers=AUTH, json={
        "provider": "manual", "items": [{"kind": "NOT_A_KIND"}],
    })
    assert res.status_code == 400


def test_등록한_기존보험을_삭제할_수_있다(client):
    created = client.post("/users/1/external-policies/link", headers=AUTH, json={
        "provider": "manual", "items": [{"kind": "ACCIDENT"}],
    }).json()
    policy_id = created[0]["external_policy_id"]

    assert client.delete(f"/users/1/external-policies/{policy_id}", headers=AUTH).status_code == 200
    assert client.get("/users/1/external-policies", headers=AUTH).json() == []


def test_여행자보험이_없으면_진단은_빈_결과다(client):
    res = client.get("/users/1/coverage-overlap", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body == {"duplicates": [], "gaps": [], "fixed_ok": [], "unknown": []}
