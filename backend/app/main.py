import traceback

import secure
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config
from app import schema_migrations
from app.database import engine
from app.limiter import limiter
from app.services.kb_provenance import synchronize_policy_fingerprints
from app import models  # noqa: F401  (모델 등록을 위해 import)
from app.routers import (
    users, trips, policies, incidents, insurers, auth, clauses, external_policies, onsite,
)

# 스키마 맞추기(없는 테이블 생성 + 기존 테이블에 새 컬럼 추가)는 app.schema_migrations에
# 있다. 앱을 띄우지 않고 DB만 여는 쪽(테스트 등)에서도 같은 코드를 부를 수 있어야 해서
# 따로 뒀다 — 그 사연은 그 모듈의 설명을 참고.
schema_migrations.apply(engine)

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


def _ensure_question_bank():
    """공용 질문 뱅크를 기동 때마다 맞춰 둔다.

    "빈 테이블이면 채운다"로는 부족하다 — 질문은 계속 늘어나는데(특히 세부유형별 질문),
    이미 행이 있는 DB에는 새 질문이 영영 안 들어간다. 시드는 target_field 기준으로
    없는 것만 추가하고 태그만 갱신하므로 몇 번을 돌려도 같은 결과다."""
    try:
        from app.seed_questions import run as seed_questions
        seed_questions()
    except Exception as exc:  # noqa: BLE001 — 어떤 이유든 앱 기동을 막지 않는다
        print(f"[startup] question_bank 시드를 건너뜁니다: {exc}")


def _ensure_actual_premiums():
    """실제 조회 보험료를 시트에 있는 보험사만큼 채워 둔다.

    "빈 테이블이면 채운다"로는 부족하다 — 보험사가 하나씩 늘어나는 자료라서(메리츠가
    나중에 들어왔다), 이미 다른 보험사 행이 있는 DB에는 새 보험사가 영영 안 들어간다.
    시트에 있는데 DB에 한 행도 없는 보험사가 하나라도 있으면 다시 적재한다."""
    from app.database import SessionLocal
    from app.models.kb import Insurer, InsurerPremium
    from app.seed_premiums_actual import DEFAULT_PATH, _SHEET_CONFIG, run as seed_premiums

    if not DEFAULT_PATH.exists():
        return
    db = SessionLocal()
    try:
        have = {
            code for (code,) in db.query(Insurer.code)
            .join(InsurerPremium, InsurerPremium.insurer_id == Insurer.insurer_id)
            .distinct()
        }
        missing = {code for code, _vertical, _std in _SHEET_CONFIG.values()} - have
        if not missing:
            return
        print(f"[startup] 보험료 자료가 없는 보험사: {', '.join(sorted(missing))} — 다시 적재합니다")
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] 보험료 적재 여부를 확인하지 못했습니다: {exc}")
        return
    finally:
        db.close()
    try:
        seed_premiums()
    except Exception as exc:  # noqa: BLE001 — 어떤 이유든 앱 기동을 막지 않는다
        print(f"[startup] 보험료 적재를 건너뜁니다: {exc}")


# 위 다섯 점검을 한자리에 모아 둔다. 예전에는 두 곳에 흩어져 있었는데(정의 사이에 호출이
# 끼어 있었다), 무엇이 기동 때 도는지 한눈에 안 보였다.
#
# config.SEED_ON_STARTUP이 꺼져 있으면 통째로 건너뛴다. 다섯 점검 모두 "비어 있으면 채운다"
# 라서, 자료가 이미 들어 있는 DB에서는 무엇도 바꾸지 않는다 — 다만 그 사실을 확인하려고
# DB 세션을 여섯 번 열고 openpyxl까지 끌어온다. 커밋된 app.db를 그대로 싣는 배포본에서는
# 그 확인이 항상 헛일이라, 무료 인스턴스에서 첫 방문자를 그만큼 더 기다리게 할 이유가 없다.
if config.SEED_ON_STARTUP:
    _ensure_doc_requirements()
    _ensure_travel_alerts()
    _ensure_onsite_and_simulation()
    _ensure_question_bank()
    _ensure_actual_premiums()

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
