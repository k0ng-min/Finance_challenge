import secure
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app import config
from app.database import Base, engine
from app.limiter import limiter
from app.services.kb_provenance import synchronize_policy_fingerprints
from app import models  # noqa: F401  (모델 등록을 위해 import)
from app.routers import users, trips, policies, incidents, insurers, auth, clauses, external_policies

Base.metadata.create_all(bind=engine)


def _add_missing_columns(table: str, additions: dict[str, str]):
    """SQLAlchemy는 기존 테이블에 새 컬럼을 자동 추가하지 않으므로, 없는 컬럼만 직접 추가한다."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        for col, ddl in additions.items():
            if col not in existing:
                conn.execute(text(ddl))
        conn.commit()


_add_missing_columns("app_user", {
    "email": "ALTER TABLE app_user ADD COLUMN email VARCHAR",
    "password_hash": "ALTER TABLE app_user ADD COLUMN password_hash VARCHAR",
    "password_salt": "ALTER TABLE app_user ADD COLUMN password_salt VARCHAR",
    "auth_provider": "ALTER TABLE app_user ADD COLUMN auth_provider VARCHAR DEFAULT 'guest'",
    "session_token": "ALTER TABLE app_user ADD COLUMN session_token VARCHAR",
    "session_expires_at": "ALTER TABLE app_user ADD COLUMN session_expires_at DATETIME",
    "kakao_id": "ALTER TABLE app_user ADD COLUMN kakao_id VARCHAR",
    "google_id": "ALTER TABLE app_user ADD COLUMN google_id VARCHAR",
    "terms_agreed_at": "ALTER TABLE app_user ADD COLUMN terms_agreed_at DATETIME",
    "privacy_agreed_at": "ALTER TABLE app_user ADD COLUMN privacy_agreed_at DATETIME",
    "marketing_agreed_at": "ALTER TABLE app_user ADD COLUMN marketing_agreed_at DATETIME",
    "age": "ALTER TABLE app_user ADD COLUMN age INTEGER",
    "sex": "ALTER TABLE app_user ADD COLUMN sex VARCHAR",
})
_add_missing_columns("trip", {
    "user_policy_id": "ALTER TABLE trip ADD COLUMN user_policy_id INTEGER",
})
_add_missing_columns("clause", {
    "highlight_spans": "ALTER TABLE clause ADD COLUMN highlight_spans TEXT",
    "plain_text": "ALTER TABLE clause ADD COLUMN plain_text TEXT",
})
_add_missing_columns("incident", {
    "user_policy_id": "ALTER TABLE incident ADD COLUMN user_policy_id INTEGER",
    "free_text": "ALTER TABLE incident ADD COLUMN free_text TEXT",
    "item_damage_type": "ALTER TABLE incident ADD COLUMN item_damage_type VARCHAR",
    "type_id": "ALTER TABLE incident ADD COLUMN type_id INTEGER",
    "modifiers": "ALTER TABLE incident ADD COLUMN modifiers TEXT",
    "classify_confidence": "ALTER TABLE incident ADD COLUMN classify_confidence FLOAT",
})
_add_missing_columns("analysis_finding", {
    "coverage_amount": "ALTER TABLE analysis_finding ADD COLUMN coverage_amount VARCHAR",
})
_add_missing_columns("user_policy", {
    "subscriber_age": "ALTER TABLE user_policy ADD COLUMN subscriber_age INTEGER",
})
_add_missing_columns("incident_type", {
    "needs_review": "ALTER TABLE incident_type ADD COLUMN needs_review BOOLEAN DEFAULT 0",
})
_add_missing_columns("question_bank", {
    "applies_to_l1": "ALTER TABLE question_bank ADD COLUMN applies_to_l1 VARCHAR",
})
_add_missing_columns("overlap_rule", {
    "anchor_phrase": "ALTER TABLE overlap_rule ADD COLUMN anchor_phrase VARCHAR",
})
_add_missing_columns("insurer_premium", {
    "period_days": "ALTER TABLE insurer_premium ADD COLUMN period_days INTEGER DEFAULT 7 NOT NULL",
})

def _ensure_doc_requirements():
    """서류 사진 확인이 인용할 약관 근거(doc_requirement)가 비어 있으면 채운다.

    저장소를 클론한 사람이 시드 스크립트를 따로 기억하지 않아도 기능이 온전히 돌게 하려는
    것이다. 위 컬럼 마이그레이션과 같은 자리에 두는 이유도 같다 — 기동 한 번으로 스키마와
    데이터가 모두 맞춰진다.

    약관이 아직 적재되지 않은 DB에서는 근거 조항을 못 찾아 시드가 예외를 던지는데, 그건
    이 상황에서 정상이므로 앱을 죽이지 않고 넘어간다. 그 경우 서류 사진 확인은 "약관에
    정해진 형식 요건 없음"으로 동작하며, 근거 없는 판정을 내리지는 않는다.
    """
    from app.database import SessionLocal
    from app.models.kb import Clause, DocRequirement

    db = SessionLocal()
    try:
        if db.query(DocRequirement).first() is not None:
            return
        if db.query(Clause).first() is None:
            return  # 약관 KB가 없는 빈 DB. 시드할 근거 자체가 없다.
        from app.seed_doc_requirements import seed
        count = seed(db)
        db.commit()
        print(f"[startup] doc_requirement {count}건 시드 완료")
    except Exception as exc:  # noqa: BLE001 — 어떤 이유든 앱 기동을 막지 않는다
        db.rollback()
        print(f"[startup] doc_requirement 시드를 건너뜁니다: {exc}")
    finally:
        db.close()


_ensure_doc_requirements()

app = FastAPI(title="여행자보험 전 생애주기 AI")

# 요청 빈도 제한 — FastAPI 생태계 표준 라이브러리(slowapi). @limiter.limit(...) 데코레이터가
# 붙은 각 엔드포인트(로그인, 카카오/구글 인증, Gemini를 호출하는 사고 접수·순위·약관 관련
# 엔드포인트)가 알아서 자기 한도를 체크하므로, 여기서는 그 결과(RateLimitExceeded)를 429
# 응답으로 바꿔주는 핸들러만 등록하면 된다.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 응답에 보안 헤더(HSTS, X-Frame-Options, X-Content-Type-Options 등)를 붙인다 —
# 역시 직접 쓰지 않고 널리 쓰이는 secure 라이브러리의 기본 프리셋을 그대로 쓴다.
_secure_headers = secure.Secure.with_default_headers()


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    await _secure_headers.set_headers_async(response)
    return response


app.include_router(users.router)
app.include_router(trips.router)
app.include_router(policies.router)
app.include_router(incidents.router)
app.include_router(insurers.router)
app.include_router(auth.router)
app.include_router(clauses.router)
app.include_router(external_policies.router)
app.include_router(external_policies.overlap_router)


@app.get("/health")
def health():
    return {"status": "ok"}
