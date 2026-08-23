import traceback

import secure
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config
from app.database import Base, engine
from app.limiter import limiter
from app.services.kb_provenance import synchronize_policy_fingerprints
from app import models  # noqa: F401  (모델 등록을 위해 import)
from app.routers import (
    users, trips, policies, incidents, insurers, auth, clauses, external_policies, onsite,
)

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
_add_missing_columns("user_policy", {
    "plan_name": "ALTER TABLE user_policy ADD COLUMN plan_name VARCHAR",
})
_add_missing_columns("clause", {
    "highlight_spans": "ALTER TABLE clause ADD COLUMN highlight_spans TEXT",
    "plain_text": "ALTER TABLE clause ADD COLUMN plain_text TEXT",
    "source_edition": "ALTER TABLE clause ADD COLUMN source_edition VARCHAR",
})
_add_missing_columns("incident", {
    "user_policy_id": "ALTER TABLE incident ADD COLUMN user_policy_id INTEGER",
    "free_text": "ALTER TABLE incident ADD COLUMN free_text TEXT",
    "item_damage_type": "ALTER TABLE incident ADD COLUMN item_damage_type VARCHAR",
    "type_id": "ALTER TABLE incident ADD COLUMN type_id INTEGER",
    "modifiers": "ALTER TABLE incident ADD COLUMN modifiers TEXT",
    "classify_confidence": "ALTER TABLE incident ADD COLUMN classify_confidence FLOAT",
    "questions_generated": "ALTER TABLE incident ADD COLUMN questions_generated BOOLEAN DEFAULT 0",
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
    "incident_id": "ALTER TABLE question_bank ADD COLUMN incident_id INTEGER",
})
_add_missing_columns("overlap_rule", {
    "anchor_phrase": "ALTER TABLE overlap_rule ADD COLUMN anchor_phrase VARCHAR",
})
_add_missing_columns("insurer_premium", {
    "period_days": "ALTER TABLE insurer_premium ADD COLUMN period_days INTEGER DEFAULT 7 NOT NULL",
})


def _migrate_insurer_premium_to_plan_schema():
    """옛 insurer_premium은 (insurer_id, sex, age)에 UNIQUE가 걸려 있어 보험사 등급별로
    여러 행을 못 넣는다. SQLite는 ALTER로 UNIQUE 제약을 못 바꾸므로, plan_name이
    없는 옛 테이블이면 통째로 지우고 새 스키마로 다시 만든다 — 2026-08-19에 보험다모아
    비교공시값을 보험사 실제 등급별 가격으로 전면 교체하면서 생긴 스키마 변경이다.
    app.seed_premiums_actual을 다시 돌리면 채워진다."""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(insurer_premium)"))}
        if existing and "plan_name" not in existing:
            conn.execute(text("DROP TABLE insurer_premium"))
            conn.commit()
            Base.metadata.create_all(bind=engine)
            print("[startup] insurer_premium을 등급별 가격 스키마로 재생성했습니다 — "
                  "python -m app.seed_premiums_actual 로 다시 채워주세요.")


_migrate_insurer_premium_to_plan_schema()

# 기존 app.db도 새 시드와 동일한 PDF 지문을 갖도록 멱등 동기화한다.
synchronize_policy_fingerprints(engine)


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


def _ensure_travel_alerts():
    """여행경보 스냅샷이 있으면 비어 있는 테이블에 채운다.

    doc_requirement와 같은 이유로 기동 시에 둔다 — 클론한 사람이 시드 명령을 따로 기억하지
    않아도 되게. 스냅샷이 아직 없으면(인증키 미발급) 조용히 넘어가고, 경보 배지와 면책
    안내만 나타나지 않는다.
    """
    from app.database import SessionLocal
    from app.models.kb import TravelAlert

    db = SessionLocal()
    try:
        if db.query(TravelAlert).first() is not None:
            return
        from app.seed_travel_alerts import seed
        count = seed(db)
        db.commit()
        if count:
            print(f"[startup] travel_alert {count}개국 적재 완료")
    except Exception as exc:  # noqa: BLE001 — 어떤 이유든 앱 기동을 막지 않는다
        db.rollback()
        print(f"[startup] 여행경보 적재를 건너뜁니다: {exc}")
    finally:
        db.close()


def _ensure_onsite_and_simulation():
    """「현지에서」·「사고 시뮬레이션」이 쓰는 시드를 비어 있을 때만 채운다.

    doc_requirement·travel_alert와 같은 이유로 기동 시에 둔다 — 저장소를 클론한 사람이
    시드 명령을 따로 기억하지 않아도 기능이 온전히 돈다.

    셋을 한 함수에 묶은 이유는 실패 처리가 같기 때문이다. 약관 KB나 사고유형이 아직
    적재되지 않은 DB에서는 근거가 없어 시드가 예외를 던지는데, 그건 이 상황에서 정상이므로
    앱을 죽이지 않는다. 그 경우 해당 화면만 비어 보이고 근거 없는 결과를 내지는 않는다.
    """
    from app.database import SessionLocal
    from app.models.kb import CountryLanguage, OnsitePhraseI18n, SimulationScenario

    seeds = [
        ("country_language", CountryLanguage, "app.seed_country_language"),
        ("onsite_phrase_i18n", OnsitePhraseI18n, "app.seed_onsite_phrases"),
        ("simulation_scenario", SimulationScenario, "app.seed_simulation_scenarios"),
    ]
    for label, model, module_path in seeds:
        db = SessionLocal()
        try:
            if db.query(model).first() is not None:
                continue
            module = __import__(module_path, fromlist=["seed"])
            count = module.seed(db)
            db.commit()
            if count:
                print(f"[startup] {label} {count}건 시드 완료")
        except Exception as exc:  # noqa: BLE001 — 어떤 이유든 앱 기동을 막지 않는다
            db.rollback()
            print(f"[startup] {label} 시드를 건너뜁니다: {exc}")
        finally:
            db.close()


_ensure_doc_requirements()
_ensure_travel_alerts()
_ensure_onsite_and_simulation()

app = FastAPI(title="여행자보험 전 생애주기 AI")

# 요청 빈도 제한 — FastAPI 생태계 표준 라이브러리(slowapi). @limiter.limit(...) 데코레이터가
# 붙은 각 엔드포인트(로그인, 카카오/구글 인증, Gemini를 호출하는 사고 접수·순위·약관 관련
# 엔드포인트)가 알아서 자기 한도를 체크하므로, 여기서는 그 결과(RateLimitExceeded)를 429
# 응답으로 바꿔주는 핸들러만 등록하면 된다.
app.state.limiter = limiter
# 이 미들웨어가 있어야 limiter의 전역 기본 한도가 적용된다. 없으면 @limiter.limit이 붙은
# 엔드포인트만 보호되고 나머지는 무제한으로 열린다(45개 중 15개만 덮여 있었다).
app.add_middleware(SlowAPIMiddleware)


# --- 오류 응답 문구 ---------------------------------------------------------
# 기본 핸들러들은 개발자용 문구를 그대로 내보낸다. 실제로 나가던 것들:
#   429 {"error":"Rate limit exceeded: 10 per 1 minute"}   영어 + 정확한 한도까지 노출
#   422 {"detail":[{"type":"string_type","loc":[...]}]}     내부 구조 노출
#   404 {"detail":"Not Found"} / 500 "Internal Server Error"
# 사용자가 읽을 이유가 없는 말이고, 한도·필드 경로처럼 공격에 참고가 되는 정보도 섞인다.
# 아래에서 전부 상황을 설명하는 한 문장으로 바꾼다.

_STATUS_MESSAGES = {
    400: "입력한 내용을 다시 확인해 주세요.",
    401: "정보를 확인할 수 없어요. 페이지를 새로고침한 뒤 다시 시도해 주세요.",
    403: "이 정보를 볼 수 있는 권한이 없어요.",
    404: "찾는 정보가 없어요. 없어졌거나 아직 만들어지지 않았을 수 있어요.",
    405: "지금은 할 수 없는 요청이에요.",
    409: "이미 처리된 요청이에요.",
    413: "파일이 너무 커요. 조금 더 작은 파일로 다시 시도해 주세요.",
    422: "입력한 내용을 다시 확인해 주세요.",
    429: "요청이 너무 잦아요. 잠시 뒤에 다시 시도해 주세요.",
    503: "지금은 이 기능을 쓸 수 없어요. 잠시 뒤에 다시 시도해 주세요.",
}
_FALLBACK_MESSAGE = "잠시 문제가 생겼어요. 다시 시도해 주세요."


def _is_user_facing(detail) -> bool:
    """우리가 직접 쓴 한국어 안내문인지. 라이브러리 기본 문구(영어)나 검증 오류 구조체는
    사용자에게 의미가 없으므로 상태코드 기반 문구로 대체한다."""
    return isinstance(detail, str) and any("가" <= ch <= "힣" for ch in detail)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    # 정확한 한도를 알려주면 우회 간격을 맞추기 쉬워진다. 몇 회인지는 밝히지 않는다.
    return JSONResponse(status_code=429, content={"detail": _STATUS_MESSAGES[429]})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    detail = exc.detail if _is_user_facing(exc.detail) else _STATUS_MESSAGES.get(
        exc.status_code, _FALLBACK_MESSAGE
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": detail},
                        headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    # 어떤 필드가 왜 틀렸는지는 서버 로그에만 남기고, 응답에는 담지 않는다.
    return JSONResponse(status_code=422, content={"detail": _STATUS_MESSAGES[422]})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """예상 못 한 오류. 스택이나 예외 메시지가 사용자에게 나가지 않게 막는다."""
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    return JSONResponse(status_code=500, content={"detail": _FALLBACK_MESSAGE})

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
app.include_router(onsite.router)


@app.get("/health")
def health():
    return {"status": "ok"}
