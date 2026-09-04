"""여행 목록이 "어느 보험에 묶인 여행인지"를 함께 알려주는지 지킨다.

사고 접수 화면은 보험을 먼저 고르고 그다음 여행을 고른다. 그런데 여행 목록 응답에
연결된 보험이 없으면, 프론트는 "이 여행이 방금 고른 보험의 여행인지"를 알 수 없어
다른 보험으로 등록해 둔 여행까지 같이 보여주게 된다. 실제로 그렇게 새고 있었다.
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.user import AppUser, Trip, UserPolicy
from app.services.auth import utc_now, hash_session_token


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, nickname: str, token: str) -> int:
    user = AppUser(
        nickname=nickname, auth_provider="guest",
        session_token=hash_session_token(token),
        session_expires_at=utc_now() + timedelta(days=1),
    )
    db.add(user)
    db.commit()
    return user.user_id


def make_policy(db, user_id: int, insurer: str) -> int:
    policy = UserPolicy(
        user_id=user_id, insurer_name_raw=insurer,
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 10),
    )
    db.add(policy)
    db.commit()
    return policy.user_policy_id


def make_trip(db, user_id: int, destination: str, user_policy_id: int | None) -> int:
    trip = Trip(
        user_id=user_id, destination=destination,
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 10),
        user_policy_id=user_policy_id,
    )
    db.add(trip)
    db.commit()
    return trip.trip_id


def test_여행_목록은_연결된_보험을_함께_알려준다(client, db_session):
    me = make_user(db_session, "본인", "my-token")
    삼성 = make_policy(db_session, me, "삼성화재")
    현대 = make_policy(db_session, me, "현대해상")

    일본 = make_trip(db_session, me, "일본", 삼성)
    베트남 = make_trip(db_session, me, "베트남", 현대)
    미정 = make_trip(db_session, me, "태국", None)

    res = client.get(f"/users/{me}/trips", headers={"Authorization": "Bearer my-token"})
    assert res.status_code == 200, res.text
    linked = {t["trip_id"]: t["user_policy_id"] for t in res.json()}

    assert linked[일본] == 삼성
    assert linked[베트남] == 현대, "다른 보험에 묶인 여행을 구분할 수 없습니다"
    assert linked[미정] is None, "아직 보험을 붙이지 않은 여행은 어느 보험에도 묶이면 안 됩니다"
