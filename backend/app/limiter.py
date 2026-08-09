"""요청 빈도 제한(rate limiting) — FastAPI 생태계에서 가장 널리 쓰이는 slowapi를 쓴다.
main.py와 routers/auth.py 양쪽에서 같은 limiter 인스턴스를 참조해야 하는데, 그냥 main.py에
두면 auth.py -> main.py -> auth.py 순환 임포트가 생긴다. 그래서 별도 모듈로 뺐다."""
import hashlib

from slowapi import Limiter
from slowapi.util import get_remote_address

# slowapi는 기본으로 프로젝트 루트의 .env를 직접 읽으려 하는데, 그 내부(starlette.config.Config)가
# OS 기본 코드페이지로 파일을 여는 바람에 이 환경(한글 Windows, cp949)에서 UTF-8로 저장된 .env를
# 읽다가 UnicodeDecodeError로 죽는다. config_filename을 존재하지 않는 경로로 줘서 그 자동 로딩
# 자체를 건너뛴다 — 실제 환경변수는 이미 config.py에서 python-dotenv(UTF-8 세이프)로 정상 로드된다.
# 전역 기본 한도. 데코레이터가 붙은 엔드포인트는 각자의 한도가 이 값을 대신한다.
# 예전에 "전역 한도가 안 먹는다"고 기록돼 있었는데, 실제로는 SlowAPIMiddleware가 앱에
# 등록되지 않은 상태였다 — 미들웨어 없이는 default_limits가 적용될 자리가 없다. 미들웨어를
# 붙이고 다시 측정해 전 엔드포인트에 걸리는 것을 확인했다.
# 값은 사람이 화면을 쓰는 속도보다 넉넉하되(연타·새로고침 포함) 자동 수집은 걸리게 잡았다.
DEFAULT_LIMITS = ["240/minute", "3000/hour"]

def client_key(request) -> str:
    """이 요청을 누구 몫으로 셀지 정한다.

    기본값인 get_remote_address는 request.client.host(=바로 앞 홉의 주소)를 쓴다. Render처럼
    리버스 프록시 뒤에서 돌면 그 값이 항상 프록시 IP라, 모든 사용자가 한 버킷에 묶인다 —
    한 명이 한도를 다 쓰면 나머지 전부가 막히고, 정작 특정 IP의 남용은 걸러지지 않는다.

    그래서 순서대로 본다.

    1) 로그인·게스트 세션 토큰. 계정 단위로 세므로 IP를 바꿔도 회피되지 않고, 같은 공용
       와이파이를 쓰는 사람들이 서로를 밀어내지도 않는다. 원문 대신 해시 앞부분만 키로 쓴다.
    2) X-Forwarded-For의 '마지막' 항목. 각 프록시는 자기가 받은 주소를 뒤에 덧붙이므로,
       신뢰하는 프록시가 하나일 때 마지막 값이 실제 클라이언트다. 첫 항목을 쓰면 클라이언트가
       가짜 IP를 앞에 붙여 한도를 무한히 우회할 수 있다.
    3) 둘 다 없으면(로컬 개발 등) 접속 주소.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token:
            return "t:" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return "ip:" + forwarded.split(",")[-1].strip()

    return "ip:" + get_remote_address(request)


limiter = Limiter(
    key_func=client_key,
    default_limits=DEFAULT_LIMITS,
    config_filename="__slowapi_skip_dotenv__",
)
