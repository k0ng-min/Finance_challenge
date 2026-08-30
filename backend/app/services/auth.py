"""이메일/비밀번호 인증. 비밀번호 해싱은 손으로 짠 코드 대신, 업계 표준인 bcrypt를 쓴다.
(passlib을 경유하는 흔한 방식도 검토했지만, passlib은 2020년 이후 관리가 끊겨 최신 bcrypt
패키지와 호환이 깨져 있다 — 실제로 이 환경에서 AttributeError로 죽는 걸 확인했다. 그래서
passlib 없이 bcrypt 패키지를 직접 쓴다. bcrypt는 해시 자체에 salt를 담고 있어 별도 salt
컬럼이 필요 없지만, 기존 DB 스키마(password_salt 컬럼)와의 호환을 위해 튜플 반환 형태는
유지한다.)"""
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_BCRYPT_MAX_BYTES = 72  # bcrypt 알고리즘 자체의 한계 — 넘는 부분은 잘라서 넣는다

# 세션을 영구히 유효하게 두지 않는다 — 오래된 토큰이 계속 살아있으면 기기 분실/탈취 시
# 위험이 커진다. 금융권은 보통 짧은 무활동 타임아웃을 쓰지만, 이 앱은 로그인당 매번
# 다시 로그인하게 만들 필요는 없는 서비스라 조금 더 여유 있게 14일로 잡는다.
SESSION_TTL_DAYS = 14


def utc_now() -> datetime:
    """지금 시각을 UTC로, 단 시간대 정보는 떼고 돌려준다.

    datetime.utcnow()는 파이썬에서 폐기 예정이라 경고가 뜬다. 그렇다고 권장 대체인
    datetime.now(timezone.utc)를 그대로 쓰면 시간대가 붙은 값이 되는데, 세션 만료를
    담는 컬럼은 시간대를 저장하지 않는 DateTime이다(models/user.py). 붙은 값과 안 붙은
    값을 비교하면 TypeError로 로그인이 통째로 깨진다. 그래서 UTC로 계산한 뒤 시간대만
    떼어, 지금까지 저장된 값들과 같은 모양을 유지한다.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def session_expiry() -> datetime:
    return utc_now() + timedelta(days=SESSION_TTL_DAYS)


def hash_password(password: str) -> tuple[str, str]:
    hashed = bcrypt.hashpw(password.encode("utf-8")[:_BCRYPT_MAX_BYTES], bcrypt.gensalt())
    return hashed.decode("utf-8"), ""


def verify_password(password: str, digest: str, salt: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:_BCRYPT_MAX_BYTES], digest.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def issue_session(user) -> str:
    """새 세션을 발급한다. DB에는 해시만 남기고, 원문은 이 반환값으로만 나간다.

    호출부는 반드시 이 반환값을 응답에 담아야 한다 — user.session_token을 그대로 쓰면
    해시가 클라이언트로 나가서 로그인이 성립하지 않는다.
    """
    token = generate_session_token()
    user.session_token = hash_session_token(token)
    user.session_expires_at = session_expiry()
    return token


def hash_session_token(token: str) -> str:
    """세션 토큰은 DB에 원문으로 두지 않는다.

    비밀번호는 bcrypt로 해싱해 두면서 토큰만 평문으로 두면, DB가 유출됐을 때 비밀번호는
    못 풀어도 살아있는 세션은 전부 그대로 탈취된다. 토큰은 원문을 클라이언트만 갖고,
    서버는 조회용 해시만 보관한다.

    여기서는 bcrypt가 아니라 SHA-256을 쓴다. 토큰은 이미 secrets.token_urlsafe(32)로 만든
    256비트 난수라 사전 공격 대상이 아니고(느린 해시가 막아주는 위협이 없다), 매 요청마다
    토큰으로 사용자를 '조회'해야 해서 bcrypt처럼 느리면 인증이 병목이 된다.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


# --- 로그인 보호 -------------------------------------------------------------
# 요청 빈도 제한(slowapi)은 토큰이나 IP 단위라, 주소를 바꿔 가며 같은 계정을 두드리는
# 대입 공격은 그대로 통과한다. 계정 자체에도 연속 실패를 세어 두고 잠근다.
#
# 값은 금융권에서 흔히 쓰는 "5회 실패 시 잠금"을 따르되, 잠금 시간은 사람이 직접 풀어야
# 하는 영구 잠금 대신 자동으로 풀리는 10분으로 둔다. 이 서비스에는 계정 잠금을 풀어 줄
# 상담 창구가 없어서, 영구 잠금은 공격자가 남의 계정을 마음대로 막아 버리는 수단
# (서비스 거부)이 되기 때문이다.
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 10

# 로그인한 계정이 이만큼 아무 요청도 보내지 않으면 세션을 만료시킨다. 자리를 비운 사이
# 남이 그 브라우저를 쓰는 상황을 막기 위한 것이고, 금융권에서 표준으로 쓰는 장치다.
# 게스트에게는 적용하지 않는다 — 로그인이 없는 사용자는 화면을 오래 들여다보다 돌아와도
# 하던 일이 이어져야 하고, 게스트 데이터는 애초에 그 브라우저 밖으로 나가지 않는다.
IDLE_TIMEOUT_MINUTES = 30


def is_locked(user) -> bool:
    """지금 이 계정이 잠금 상태인가."""
    locked_until = getattr(user, "locked_until", None)
    return bool(locked_until and locked_until > utc_now())


def register_failed_login(user) -> bool:
    """로그인 실패를 계정에 기록한다. 이번 실패로 잠기게 됐으면 True.

    커밋은 부르는 쪽 몫이다 — 로그인 실패는 예외로 끝나는 경로라, 부르는 쪽이 예외를
    던지기 전에 반드시 커밋해야 이 기록이 남는다.
    """
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= MAX_FAILED_LOGINS:
        user.locked_until = utc_now() + timedelta(minutes=LOCKOUT_MINUTES)
        user.failed_login_count = 0  # 잠금이 풀린 뒤 처음부터 다시 센다
        return True
    return False


def clear_failed_logins(user) -> None:
    """로그인에 성공했으니 실패 기록과 잠금을 지운다."""
    user.failed_login_count = 0
    user.locked_until = None


def dummy_password_check() -> None:
    """계정이 없을 때도 있을 때와 같은 시간을 쓰게 만든다.

    응답 문구는 이미 "이메일이 없음"과 "비밀번호가 틀림"을 구분하지 않는데, 정작 걸리는
    시간이 달랐다 — 계정이 없으면 bcrypt 검증을 아예 건너뛰고 즉시 401이 나가고, 있으면
    bcrypt를 한 번 돌린 뒤(수십~수백 밀리초) 401이 나간다. 그 차이만 재도 어떤 이메일이
    가입돼 있는지 밖에서 훑을 수 있다(계정 열거). 없는 계정에도 같은 비용의 검증을 한 번
    돌려서 그 차이를 없앤다.
    """
    verify_password("dummy-password", _dummy_hash(), "")


#: dummy_password_check가 쓸 고정 해시. 처음 쓸 때 한 번만 만들고 그다음부터 재사용한다.
_DUMMY_HASH_CACHE: str | None = None


def _dummy_hash() -> str:
    """비교용 더미 해시를 처음 필요할 때 만든다.

    모듈을 읽을 때 미리 만들어 두는 편이 코드는 단순한데, bcrypt 해시 한 번이 이 환경에서
    0.23초다. 앱 기동이 1.15초인데 그중 0.2초를 로그인 한 번 안 해도 늘 내는 셈이라
    (무료 인스턴스가 잠에서 깰 때마다 첫 방문자가 그만큼 더 기다린다) 쓰는 자리로 미룬다.
    한 번 만든 값은 프로세스가 사는 동안 재사용하므로, 매번 만들어서 오히려 시간 편차가
    생기는 일도 없다 — 그 편차를 없애는 게 이 함수의 목적이라 중요한 부분이다.
    """
    global _DUMMY_HASH_CACHE
    if _DUMMY_HASH_CACHE is None:
        _DUMMY_HASH_CACHE = hash_password(secrets.token_urlsafe(16))[0]
    return _DUMMY_HASH_CACHE


def idle_expired(user) -> bool:
    """로그인 계정이 무활동 시간을 넘겼는가. 게스트와 기록이 없는 세션은 대상이 아니다."""
    if not getattr(user, "email", None):
        return False  # 게스트
    last_seen = getattr(user, "last_seen_at", None)
    if last_seen is None:
        return False  # 이 장치가 생기기 전에 만들어진 세션 — 다음 요청부터 기록된다
    return last_seen < utc_now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES)


# --- 비밀번호 정책 -----------------------------------------------------------
# 길이만 8자로 보던 것을 조금 더 본다. 여기서 막고 싶은 것은 "복잡한 비밀번호를 강요하기"가
# 아니라 "대입 몇 번에 뚫리는 비밀번호를 막기"다 — 그래서 특수문자를 강제하는 대신,
# 실제로 공격에 먼저 시도되는 것들(연속된 숫자, 흔한 단어, 자기 이메일)을 걸러낸다.
MIN_PASSWORD_LENGTH = 8

#: 유출된 비밀번호 목록에서 늘 상위에 오는 것들. 전수 목록을 들고 있을 자리는 아니고,
#: 실제로 제일 먼저 시도되는 형태만 막는다.
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890",
    "qwerty123", "qwertyuiop", "abc12345", "iloveyou", "admin123", "letmein1",
    "1q2w3e4r", "1qaz2wsx", "asdfasdf", "11111111", "00000000", "987654321",
}


def password_policy_error(password: str, *, email: str | None = None, nickname: str | None = None) -> str | None:
    """비밀번호가 정책에 어긋나면 사용자에게 보여줄 한 문장, 통과하면 None.

    문구는 무엇이 문제인지 정확히 알려준다 — "규칙에 맞지 않습니다"로 뭉뚱그리면
    사용자가 될 때까지 아무 값이나 넣어 보게 되고, 그러다 더 약한 비밀번호로 끝난다.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상으로 정해주세요."

    kinds = sum([
        bool(re.search(r"[a-zA-Z]", password)),
        bool(re.search(r"\d", password)),
        bool(re.search(r"[^a-zA-Z0-9]", password)),
    ])
    if kinds < 2:
        return "영문·숫자·기호 중 두 가지 이상을 섞어 주세요."

    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        return "너무 많이 쓰이는 비밀번호예요. 다른 비밀번호로 정해주세요."

    # 같은 글자 반복(aaaaaaaa)과 연속된 나열(12345678, abcdefgh)은 길이만 채운 비밀번호다.
    if len(set(password)) <= 2:
        return "같은 글자만 반복하지 말고 다른 글자를 섞어 주세요."
    if _is_sequential(lowered):
        return "연속된 문자나 숫자만으로는 정할 수 없어요."

    # 자기 이메일 아이디나 닉네임이 그대로 들어간 비밀번호는 아는 사람이 바로 맞힌다.
    local_part = (email or "").split("@")[0].lower()
    for hint in (local_part, (nickname or "").lower()):
        if len(hint) >= 4 and hint in lowered:
            return "이메일이나 닉네임이 그대로 들어간 비밀번호는 쓸 수 없어요."

    return None


def _is_sequential(text: str) -> bool:
    """전체가 오름차순/내림차순 연속인지(1234..., dcba...)."""
    if len(text) < 4:
        return False
    diffs = {ord(b) - ord(a) for a, b in zip(text, text[1:])}
    return diffs in ({1}, {-1})
