"""이메일/비밀번호 인증. 비밀번호 해싱은 손으로 짠 코드 대신, 업계 표준인 bcrypt를 쓴다.
(passlib을 경유하는 흔한 방식도 검토했지만, passlib은 2020년 이후 관리가 끊겨 최신 bcrypt
패키지와 호환이 깨져 있다 — 실제로 이 환경에서 AttributeError로 죽는 걸 확인했다. 그래서
passlib 없이 bcrypt 패키지를 직접 쓴다. bcrypt는 해시 자체에 salt를 담고 있어 별도 salt
컬럼이 필요 없지만, 기존 DB 스키마(password_salt 컬럼)와의 호환을 위해 튜플 반환 형태는
유지한다.)"""
import re
import secrets
from datetime import datetime, timedelta

import bcrypt

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_BCRYPT_MAX_BYTES = 72  # bcrypt 알고리즘 자체의 한계 — 넘는 부분은 잘라서 넣는다

# 세션을 영구히 유효하게 두지 않는다 — 오래된 토큰이 계속 살아있으면 기기 분실/탈취 시
# 위험이 커진다. 금융권은 보통 짧은 무활동 타임아웃을 쓰지만, 이 앱은 로그인당 매번
# 다시 로그인하게 만들 필요는 없는 서비스라 조금 더 여유 있게 14일로 잡는다.
SESSION_TTL_DAYS = 14


def session_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)


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


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))
