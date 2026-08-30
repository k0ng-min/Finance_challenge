"""남의 데이터에 접근할 수 없는지 검증한다.

원래 verify_owner는 토큰이 있을 때만 소유권을 확인했다. "게스트는 로그인 없이 자기
user_id만 들고 쓰는 구조"라는 전제였는데, 그 전제를 서버가 확인할 방법이 없다는 게
문제였다 — 토큰을 빼고 user_id만 바꿔 부르면 남의 여행·보험·사고가 그대로 나왔고,
user_id가 순차 정수라 1부터 훑으면 전수 수집이 가능했다.

지금은 게스트에게도 세션 토큰을 발급하고, 모든 소유권 검사가 토큰을 요구한다.
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.user import AppUser
from app.services.auth import utc_now, hash_session_token

# 사용자별 데이터를 돌려주는 엔드포인트. 하나라도 빠지면 그 구멍으로 전부 새어나간다.
OWNED_PATHS = [
    "/users/{uid}/trips",
    "/users/{uid}/policies",
    "/users/{uid}/incidents",
    "/users/{uid}/external-policies",
]


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


def test_토큰_없이는_남의_데이터를_볼_수_없다(client, db_session):
    victim = make_user(db_session, "피해자", "victim-token")

    for path in OWNED_PATHS:
        res = client.get(path.format(uid=victim))
        assert res.status_code == 401, (
            f"{path}: 토큰 없이 {res.status_code}로 통과했습니다 — 남의 데이터가 노출됩니다"
        )


def test_다른_사람_토큰으로도_볼_수_없다(client, db_session):
    victim = make_user(db_session, "피해자", "victim-token")
    make_user(db_session, "공격자", "attacker-token")

    for path in OWNED_PATHS:
        res = client.get(path.format(uid=victim), headers={"Authorization": "Bearer attacker-token"})
        assert res.status_code == 403, f"{path}: 남의 토큰으로 {res.status_code}"


def test_본인_토큰이면_정상_조회된다(client, db_session):
    me = make_user(db_session, "본인", "my-token")

    for path in OWNED_PATHS:
        res = client.get(path.format(uid=me), headers={"Authorization": "Bearer my-token"})
        assert res.status_code == 200, f"{path}: 본인인데 {res.status_code} — {res.text[:80]}"


def test_게스트_생성_시_토큰을_함께_준다(client):
    """게스트도 토큰이 있어야 자기 데이터를 다시 꺼낼 수 있다. 토큰을 안 주면
    프론트가 아무것도 조회하지 못하거나, 예전처럼 토큰 없는 접근을 열어둘 수밖에 없다."""
    res = client.post("/users", json={"nickname": "게스트"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("token"), "게스트 생성 응답에 토큰이 없습니다"

    listed = client.get(f"/users/{body['user_id']}/trips",
                        headers={"Authorization": f"Bearer {body['token']}"})
    assert listed.status_code == 200


def test_세션_토큰은_DB에_평문으로_남지_않는다(client, db_session):
    """DB가 유출돼도 세션을 곧바로 탈취할 수 없어야 한다."""
    res = client.post("/users", json={"nickname": "게스트"})
    token = res.json()["token"]

    user = db_session.get(AppUser, res.json()["user_id"])
    assert user.session_token != token, "세션 토큰이 평문으로 저장돼 있습니다"
    assert user.session_token == hash_session_token(token)


def test_기한이_지난_세션은_거부되고_토큰이_지워진다(client, db_session):
    """만료 검사는 저장된 시각(시간대 없음)과 지금 시각을 직접 비교한다.

    이 비교가 지금까지 테스트를 통과한 적이 없었다 — 기존 테스트는 전부 넉넉히 살아
    있는 세션만 만들어서, 만료된 쪽 가지로는 한 번도 들어가지 않았다. 시각을 다루는
    방식을 바꿀 때(예: utcnow -> utc_now) 여기가 조용히 깨지면 로그인 전체가 막히므로
    양쪽 가지를 모두 지나가게 둔다.
    """
    user = AppUser(
        nickname="만료된사람", auth_provider="guest",
        session_token=hash_session_token("stale-token"),
        session_expires_at=utc_now() - timedelta(seconds=1),
    )
    db_session.add(user)
    db_session.commit()

    res = client.get("/auth/me", headers={"Authorization": "Bearer stale-token"})
    assert res.status_code == 401, f"만료된 세션이 {res.status_code}로 통과했습니다"

    db_session.refresh(user)
    assert user.session_token is None, "만료된 세션의 토큰이 DB에 그대로 남아 있습니다"
