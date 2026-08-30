"""보안 사건을 감사 로그(security_event)에 남긴다.

왜 애플리케이션 로그가 아니라 표인가. Render 같은 호스팅에서 표준 출력 로그는 재배포하면
사라지고 보존 기간도 짧다. "누가 언제 남의 데이터에 접근하려 했는가"는 사고가 난 뒤에야
찾게 되는 기록이라, 그때 이미 지워져 있으면 없는 것과 같다.

무엇을 남기지 않는지가 무엇을 남기는지만큼 중요하다.

- 비밀번호와 세션 토큰은 원문도 해시도 남기지 않는다.
- 사고 내용·진단명 같은 민감정보를 detail에 넣지 않는다.
- 접속 주소는 원문 대신 해시 앞자리만 남긴다. 같은 곳에서 반복된 시도인지는 셀 수 있지만
  주소 자체는 복원되지 않는다.

감사 로그가 유출되면 그것 자체가 2차 사고가 되기 때문이다.
"""
from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.models.user import SecurityEvent

# 사건 종류. 문자열을 여기저기 흩어 쓰면 오타가 조용히 다른 종류를 만들어 내므로 모아 둔다.
LOGIN_SUCCESS = "login_success"
LOGIN_FAILED = "login_failed"
LOGIN_BLOCKED = "login_blocked"          # 잠긴 계정에 로그인 시도
ACCOUNT_LOCKED = "account_locked"        # 연속 실패로 방금 잠금
PASSWORD_CHANGED = "password_changed"
SESSION_EXPIRED = "session_expired"
SESSION_IDLE_EXPIRED = "session_idle_expired"
OWNERSHIP_VIOLATION = "ownership_violation"  # 남의 데이터에 접근 시도
ACCOUNT_DELETED = "account_deleted"

#: detail에 담는 한 줄의 길이 상한. 길면 그 자체로 개인정보가 섞일 위험이 커진다.
_DETAIL_MAX = 200


def client_fingerprint(request) -> str | None:
    """접속 주소를 되돌릴 수 없는 짧은 지문으로 바꾼다.

    limiter.client_key와 달리 세션 토큰은 쓰지 않는다. 토큰에서 파생된 값을 감사 로그에
    남기면, 로그를 가진 쪽이 "이 사건과 저 사건이 같은 세션"임을 넘어 세션 자체를 추적하는
    수단이 된다. 여기서 필요한 것은 "같은 접속처에서 반복됐는가"뿐이다.
    """
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        raw = forwarded.split(",")[-1].strip()
    elif getattr(request, "client", None):
        raw = request.client.host
    else:
        return None
    if not raw:
        return None
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def record(
    db: Session,
    event_type: str,
    *,
    user_id: int | None = None,
    request=None,
    detail: str | None = None,
) -> None:
    """사건 하나를 남긴다.

    커밋은 하지 않는다 — 부르는 쪽의 트랜잭션에 얹혀서, 그 요청이 실패해 되돌아가면 기록도
    같이 되돌아가게 하려는 것이다. 로그인 실패처럼 예외로 끝나는 경로는 부르는 쪽에서
    명시적으로 커밋한다(그 사건이야말로 남아야 하는 기록이라서).

    기록에 실패해도 요청 자체를 죽이지 않는다. 감사 로그를 남기지 못하는 것과 사용자가
    기능을 아예 못 쓰는 것 중에서는 전자가 낫다.
    """
    try:
        db.add(SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            client_hash=client_fingerprint(request),
            target=f"{request.method} {request.url.path}" if request is not None else None,
            detail=(detail or "")[:_DETAIL_MAX] or None,
        ))
    except Exception:  # noqa: BLE001 — 감사 실패가 기능 실패가 되지 않게 한다
        pass
