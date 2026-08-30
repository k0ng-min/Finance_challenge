"""금융권에서 표준으로 쓰는 로그인·세션 보호 장치가 실제로 동작하는지 검증한다.

이 파일이 지키는 것은 네 가지다.

1. 계정 잠금 — 요청 빈도 제한만으로는 못 막는 대입 공격(주소를 바꿔 가며 같은 계정을
   두드리는 경우)을 계정 단위로 막는다.
2. 유휴 세션 만료 — 자리를 비운 사이 남이 그 브라우저를 쓰는 상황을 막는다.
3. 비밀번호 정책 — 대입 몇 번에 뚫리는 비밀번호를 거른다.
4. 보안 감사 로그 — 위 사건들이 사후에 확인 가능한 형태로 남되, 자격증명은 남지 않는다.
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.limiter import limiter
from app.main import app
from app.models.user import AppUser, SecurityEvent
from app.services import security_audit
from app.services.auth import (
    IDLE_TIMEOUT_MINUTES, MAX_FAILED_LOGINS, hash_password, hash_session_token,
    password_policy_error, utc_now,
)

PASSWORD = "Travel2026!"


@pytest.fixture(autouse=True)
def _no_rate_limit():
    """요청 빈도 제한을 잠시 끈다.

    slowapi의 카운터는 프로세스 안에서 계속 누적돼서, 로그인을 여러 번 두드리는 이 파일의
    테스트들이 서로의 한도를 갉아먹는다(뒤 테스트가 429로 끝나 정작 검증하려던 계정 잠금에
    닿지 못했다). 여기서 확인하려는 것은 "빈도 제한"이 아니라 "계정 잠금"이다 — 둘은 서로
    다른 층의 방어이고, 빈도 제한은 그것대로 이미 켜져 있다.
    """
    limiter.enabled = False
    yield
    limiter.enabled = True
    limiter.reset()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_account(db, *, email="user@example.com", token="live-token") -> AppUser:
    """비밀번호 로그인이 가능한 소셜 계정(이 앱의 유일한 가입 경로).

    kakao_id는 이메일에서 파생한다 — 계정을 둘 이상 만드는 테스트에서 같은 값을 쓰면
    유일성 제약에 걸린다.
    """
    digest, salt = hash_password(PASSWORD)
    user = AppUser(
        nickname="여행자", email=email, auth_provider="kakao", kakao_id=f"kakao-{email}",
        password_hash=digest, password_salt=salt,
        session_token=hash_session_token(token),
        session_expires_at=utc_now() + timedelta(days=1),
        last_seen_at=utc_now(),
    )
    db.add(user)
    db.commit()
    return user


def events(db, event_type: str) -> list[SecurityEvent]:
    return db.query(SecurityEvent).filter(SecurityEvent.event_type == event_type).all()


# --- 계정 잠금 ---------------------------------------------------------------

def test_연속_실패가_쌓이면_계정이_잠긴다(client, db_session):
    """요청 빈도 제한은 IP·토큰 단위라 주소를 바꾸면 우회된다. 계정 자체가 잠겨야 한다."""
    user = make_account(db_session)

    for _ in range(MAX_FAILED_LOGINS):
        res = client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})
        assert res.status_code == 401, res.text

    # 이제는 올바른 비밀번호로도 들어갈 수 없다 — 이게 잠금의 핵심이다.
    res = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert res.status_code == 401, f"잠긴 계정이 {res.status_code}로 통과했습니다"

    db_session.refresh(user)
    assert user.locked_until is not None


def test_잠금_시간이_지나면_다시_로그인할_수_있다(client, db_session):
    """자동으로 풀려야 한다. 영구 잠금이면 공격자가 남의 계정을 막는 수단이 된다."""
    user = make_account(db_session)
    for _ in range(MAX_FAILED_LOGINS):
        client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})

    db_session.refresh(user)
    user.locked_until = utc_now() - timedelta(seconds=1)  # 잠금 시간이 막 지난 상태
    db_session.commit()

    res = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert res.status_code == 200, res.text


def test_로그인에_성공하면_실패_기록이_지워진다(client, db_session):
    """지워지지 않으면 오랫동안 쓰다 오타 몇 번에 잠긴다."""
    user = make_account(db_session)
    for _ in range(MAX_FAILED_LOGINS - 1):
        client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})
    db_session.refresh(user)
    assert user.failed_login_count == MAX_FAILED_LOGINS - 1

    assert client.post("/auth/login", json={"email": user.email, "password": PASSWORD}).status_code == 200
    db_session.refresh(user)
    assert user.failed_login_count == 0
    assert user.locked_until is None


def test_없는_계정에_로그인해도_문구가_같다(client, db_session):
    """어떤 이메일이 가입돼 있는지 밖에서 훑을 수 없어야 한다."""
    user = make_account(db_session)
    있는계정 = client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})
    없는계정 = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})

    assert 있는계정.status_code == 없는계정.status_code == 401
    assert 있는계정.json() == 없는계정.json(), "응답 문구가 달라 계정 존재 여부가 드러납니다"


# --- 유휴 세션 만료 -----------------------------------------------------------

def test_오래_쓰지_않은_로그인_세션은_만료된다(client, db_session):
    user = make_account(db_session)
    user.last_seen_at = utc_now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES + 1)
    db_session.commit()

    res = client.get("/auth/me", headers={"Authorization": "Bearer live-token"})
    assert res.status_code == 401, f"무활동 세션이 {res.status_code}로 통과했습니다"
    db_session.refresh(user)
    assert user.session_token is None, "만료된 세션의 토큰이 남아 있습니다"


def test_계속_쓰는_세션은_만료되지_않는다(client, db_session):
    user = make_account(db_session)
    user.last_seen_at = utc_now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES - 1)
    db_session.commit()

    assert client.get("/auth/me", headers={"Authorization": "Bearer live-token"}).status_code == 200
    db_session.refresh(user)
    # 요청을 보냈으니 기준점이 갱신돼, 다음 판정은 지금부터 다시 센다.
    assert user.last_seen_at > utc_now() - timedelta(minutes=1)


def test_게스트_세션에는_유휴_만료를_적용하지_않는다(client, db_session):
    """게스트는 로그인할 수단이 없어서, 끊으면 하던 일을 되찾을 방법이 없다."""
    guest = AppUser(
        nickname="게스트", auth_provider="guest",
        session_token=hash_session_token("guest-token"),
        session_expires_at=utc_now() + timedelta(days=1),
        last_seen_at=utc_now() - timedelta(days=3),
    )
    db_session.add(guest)
    db_session.commit()

    res = client.get(f"/users/{guest.user_id}/trips", headers={"Authorization": "Bearer guest-token"})
    assert res.status_code == 200, f"게스트가 무활동으로 끊겼습니다({res.status_code})"


# --- 비밀번호 정책 -------------------------------------------------------------

@pytest.mark.parametrize("weak", ["short1!", "12345678", "password123", "aaaaaaaa", "abcdefgh", "onlyletters"])
def test_약한_비밀번호는_거부된다(weak):
    assert password_policy_error(weak) is not None, f"{weak!r}가 정책을 통과했습니다"


@pytest.mark.parametrize("ok", ["Travel2026!", "namsan-1994", "K9pencil!"])
def test_쓸_만한_비밀번호는_통과한다(ok):
    assert password_policy_error(ok) is None, f"{ok!r}가 막혔습니다"


def test_자기_이메일이_들어간_비밀번호는_거부된다():
    assert password_policy_error("kyungmin2026", email="kyungmin@example.com") is not None


# --- 보안 감사 로그 -------------------------------------------------------------

def test_로그인_성공과_실패가_모두_기록된다(client, db_session):
    user = make_account(db_session)
    client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})
    client.post("/auth/login", json={"email": user.email, "password": PASSWORD})

    실패 = events(db_session, security_audit.LOGIN_FAILED)
    성공 = events(db_session, security_audit.LOGIN_SUCCESS)
    assert len(실패) == 1 and 실패[0].user_id == user.user_id
    assert len(성공) == 1 and 성공[0].user_id == user.user_id
    assert 성공[0].target == "POST /auth/login"


def test_계정_잠금이_기록된다(client, db_session):
    user = make_account(db_session)
    for _ in range(MAX_FAILED_LOGINS):
        client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})
    assert len(events(db_session, security_audit.ACCOUNT_LOCKED)) == 1


def test_남의_데이터_접근_시도가_기록된다(client, db_session):
    """403 응답은 main.audit_forbidden_requests가 한 자리에서 모아 기록한다.

    그 미들웨어는 요청의 DB 세션을 받을 수 없어서(미들웨어에는 의존성 주입이 닿지 않는다)
    app.database.SessionLocal로 직접 연다. 운영에서는 둘이 같은 DB라 문제가 없지만,
    테스트는 요청 세션만 인메모리로 갈아끼우므로 여기서는 미들웨어가 실제로 쓰는 쪽을
    열어서 확인한다.
    """
    from app.database import SessionLocal

    피해자 = make_account(db_session, email="victim@example.com", token="victim-token")
    make_account(db_session, email="attacker@example.com", token="attacker-token")

    audit_db = SessionLocal()
    try:
        before = len(events(audit_db, security_audit.OWNERSHIP_VIOLATION))
    finally:
        audit_db.close()

    res = client.get(f"/users/{피해자.user_id}/trips", headers={"Authorization": "Bearer attacker-token"})
    assert res.status_code == 403

    audit_db = SessionLocal()
    try:
        rows = events(audit_db, security_audit.OWNERSHIP_VIOLATION)
        assert len(rows) == before + 1, "남의 데이터 접근 시도가 감사 로그에 남지 않았습니다"
        assert rows[-1].target == "GET /users/%d/trips" % 피해자.user_id
    finally:
        audit_db.close()


def test_감사_로그에_비밀번호나_토큰이_남지_않는다(client, db_session):
    """감사 로그가 유출되면 그것 자체가 2차 사고가 된다."""
    user = make_account(db_session)
    client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})
    client.post("/auth/login", json={"email": user.email, "password": PASSWORD})

    for row in db_session.query(SecurityEvent).all():
        blob = " ".join(str(v) for v in (row.detail, row.target, row.client_hash) if v)
        assert PASSWORD not in blob, "감사 로그에 비밀번호가 남았습니다"
        assert "wrong-password" not in blob, "감사 로그에 시도한 비밀번호가 남았습니다"
        assert "live-token" not in blob, "감사 로그에 세션 토큰이 남았습니다"
        assert hash_session_token("live-token") not in blob, "감사 로그에 토큰 해시가 남았습니다"


def test_접속_주소는_원문_대신_지문으로_남는다(client, db_session, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "AUDIT_HASH_KEY", "test-audit-key")
    user = make_account(db_session)
    client.post("/auth/login", json={"email": user.email, "password": PASSWORD},
                headers={"X-Forwarded-For": "203.0.113.7"})

    성공 = events(db_session, security_audit.LOGIN_SUCCESS)
    assert len(성공) == 1
    fingerprint = 성공[0].client_hash
    assert fingerprint and "203.0.113.7" not in fingerprint, "접속 주소가 원문으로 남았습니다"
    # 같은 곳에서 온 요청인지는 셀 수 있어야 한다 — 그래야 반복 시도를 알아본다.
    assert fingerprint == security_audit.client_fingerprint(
        type("R", (), {"headers": {"x-forwarded-for": "203.0.113.7"}, "client": None})()
    )


def test_잠긴_계정과_없는_계정의_응답이_구분되지_않는다(client, db_session):
    """잠금이 계정 열거 수단이 되면 안 된다.

    처음에는 잠긴 계정에 429와 "너무 많이 시도했다"는 별도 문구를 줬는데, 없는 이메일은
    잠길 수가 없어서(잠금은 실제 계정에만 걸린다) 아무리 두드려도 401만 나왔다. 즉 아무
    이메일에나 다섯 번 틀린 뒤 한 번 더 넣어 보면, 429가 오는지 401이 오는지로 가입 여부가
    그대로 갈렸다. 응답 시간까지 맞춰 놓고 상태코드로 그 정보를 흘리는 셈이었다.
    """
    user = make_account(db_session, email="real@example.com", token="real-token")

    for _ in range(MAX_FAILED_LOGINS):
        client.post("/auth/login", json={"email": user.email, "password": "wrong-password"})
        client.post("/auth/login", json={"email": "ghost@example.com", "password": "wrong-password"})

    db_session.refresh(user)
    assert user.locked_until is not None, "테스트 전제가 깨졌습니다 — 계정이 잠기지 않았습니다"

    잠긴계정 = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    없는계정 = client.post("/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})

    assert 잠긴계정.status_code == 없는계정.status_code, (
        f"상태코드가 갈립니다({잠긴계정.status_code} vs {없는계정.status_code}) — "
        "가입 여부가 드러납니다"
    )
    assert 잠긴계정.json() == 없는계정.json(), "응답 문구가 갈려 가입 여부가 드러납니다"

    # 그래도 잠긴 사실 자체는 감사 로그에 남아 있어야 운영자가 알아볼 수 있다.
    assert len(events(db_session, security_audit.LOGIN_BLOCKED)) >= 1


def test_비밀키가_없으면_접속_주소를_아예_남기지_않는다(client, db_session, monkeypatch):
    """소금 없는 해시는 IPv4 43억 개를 훑으면 복원된다 — 그럴 바엔 남기지 않는다."""
    from app import config

    monkeypatch.setattr(config, "AUDIT_HASH_KEY", "")
    user = make_account(db_session)
    client.post("/auth/login", json={"email": user.email, "password": PASSWORD},
                headers={"X-Forwarded-For": "203.0.113.7"})

    성공 = events(db_session, security_audit.LOGIN_SUCCESS)
    assert len(성공) == 1
    assert 성공[0].client_hash is None, "비밀키가 없는데 주소 지문이 남았습니다"


def test_비밀키가_다르면_같은_주소도_다른_지문이_된다(monkeypatch):
    """키를 모르면 지문에서 주소를 되짚을 수 없어야 한다."""
    from app import config

    fake_request = type("R", (), {"headers": {"x-forwarded-for": "203.0.113.7"}, "client": None})()

    monkeypatch.setattr(config, "AUDIT_HASH_KEY", "key-one")
    첫번째 = security_audit.client_fingerprint(fake_request)
    monkeypatch.setattr(config, "AUDIT_HASH_KEY", "key-two")
    두번째 = security_audit.client_fingerprint(fake_request)

    assert 첫번째 and 두번째
    assert 첫번째 != 두번째, "키를 바꿔도 지문이 같습니다 — 키가 섞이지 않았습니다"
