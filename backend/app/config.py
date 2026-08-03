import os
from dotenv import load_dotenv

load_dotenv()

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

# CORS를 "*"로 열어두면 어떤 사이트에서든 이 API를 불러다 쓸 수 있어(특히 로그인 토큰이 오가는
# 인증 API에서) 위험하다. 실제로 이 프론트만 접근하도록 명시한 origin만 허용한다.
# 배포 시엔 CORS_ORIGINS 환경변수에 콤마로 실제 도메인을 넣어 덮어쓴다.
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", f"{FRONTEND_BASE_URL},http://localhost:5173,http://127.0.0.1:5173,http://localhost:5183,http://127.0.0.1:5183"
).split(",") if o.strip()]

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
KAKAO_REDIRECT_URI = f"{FRONTEND_BASE_URL}/auth/kakao/callback"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = f"{FRONTEND_BASE_URL}/auth/google/callback"

KAKAO_LOGIN_ENABLED = bool(KAKAO_REST_API_KEY and KAKAO_CLIENT_SECRET)
GOOGLE_LOGIN_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# gemini-flash-latest(현재 gemini-3.6-flash)는 무료 티어 일일 20회로 매우 적어서,
# 구조화 추출처럼 깊은 추론이 필요 없는 작업엔 무료 한도가 훨씬 넉넉한(일 ~1,000회) 경량 모델을 기본값으로 쓴다.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_ENABLED = bool(GEMINI_API_KEY)

# 기존보험 수집에 쓸 방식. codef는 주민등록번호 처리 요건을 갖춘 뒤에만 켠다.
EXTERNAL_POLICY_PROVIDERS = [
    p.strip() for p in os.getenv("EXTERNAL_POLICY_PROVIDERS", "manual,mock").split(",")
    if p.strip()
]
