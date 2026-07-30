"""요청 빈도 제한(rate limiting) — FastAPI 생태계에서 가장 널리 쓰이는 slowapi를 쓴다.
main.py와 routers/auth.py 양쪽에서 같은 limiter 인스턴스를 참조해야 하는데, 그냥 main.py에
두면 auth.py -> main.py -> auth.py 순환 임포트가 생긴다. 그래서 별도 모듈로 뺐다."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# slowapi는 기본으로 프로젝트 루트의 .env를 직접 읽으려 하는데, 그 내부(starlette.config.Config)가
# OS 기본 코드페이지로 파일을 여는 바람에 이 환경(한글 Windows, cp949)에서 UTF-8로 저장된 .env를
# 읽다가 UnicodeDecodeError로 죽는다. config_filename을 존재하지 않는 경로로 줘서 그 자동 로딩
# 자체를 건너뛴다 — 실제 환경변수는 이미 config.py에서 python-dotenv(UTF-8 세이프)로 정상 로드된다.
# default_limits(전역 기본 한도)는 일부러 안 썼다 — SlowAPIMiddleware가 요청을 라우트
# 핸들러와 매칭시키는 방식이 FastAPI의 APIRouter(include_router로 나눠 등록한 서브라우터)
# 구조에서 제대로 안 먹는 걸 실측으로 확인했다(데코레이터 없는 엔드포인트를 65번 두들겨도
# 하나도 안 막힘). 그래서 신뢰할 수 있는 방식인 @limiter.limit(...) 데코레이터를 Gemini를
# 호출하는(=API 키 비용과 직결되는) 엔드포인트마다 직접 붙인다.
limiter = Limiter(key_func=get_remote_address, config_filename="__slowapi_skip_dotenv__")
