"""이미 만들어져 있는 DB에 새 컬럼을 붙이는 자리.

SQLAlchemy의 `create_all`은 없는 **테이블**만 만들고, 기존 테이블에 **컬럼**을 추가하지는
않는다. 그래서 모델에 컬럼을 하나 더하면 새로 만든 DB에서는 되고 이미 있는 DB에서는
`no such column`으로 죽는다. 여기 모아 둔 것이 그 차이를 메우는 코드다.

여태 이 코드는 `main.py` 안에 모듈 최상위 문장으로 있었다. 그러면 앱을 띄울 때는 돌지만
**앱을 띄우지 않고 DB만 여는 쪽에서는 돌지 않는다** — 실제로 커밋된 `data/app.db`를 복사해
쓰는 테스트(conftest의 `kb_session`)가 그 사본에 새 컬럼이 없어 깨졌다. 그런데도 한동안
멀쩡해 보였던 이유가 더 문제였다: 테스트가 `app.main`을 import하는 순간 이 마이그레이션이
**커밋 대상인 운영 DB 파일에** 돌아서 컬럼을 붙여 놓았기 때문이다. 즉 통과의 근거가
"테스트가 원본 파일을 고쳤다"였다.

`apply(engine)`로 떼어 두면 앱 기동과 테스트가 같은 코드를 각자의 DB에 부른다.
"""
from sqlalchemy import text

from app.database import Base

#: 테이블 -> {컬럼 이름: 그 컬럼을 추가하는 DDL}
_COLUMN_ADDITIONS: dict[str, dict[str, str]] = {
    "app_user": {
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
        "failed_login_count": "ALTER TABLE app_user ADD COLUMN failed_login_count INTEGER DEFAULT 0",
        "locked_until": "ALTER TABLE app_user ADD COLUMN locked_until DATETIME",
        "last_seen_at": "ALTER TABLE app_user ADD COLUMN last_seen_at DATETIME",
    },
    "trip": {
        "user_policy_id": "ALTER TABLE trip ADD COLUMN user_policy_id INTEGER",
    },
    "clause": {
        "highlight_spans": "ALTER TABLE clause ADD COLUMN highlight_spans TEXT",
        "plain_text": "ALTER TABLE clause ADD COLUMN plain_text TEXT",
        "source_edition": "ALTER TABLE clause ADD COLUMN source_edition VARCHAR",
    },
    "incident": {
        "user_policy_id": "ALTER TABLE incident ADD COLUMN user_policy_id INTEGER",
        "free_text": "ALTER TABLE incident ADD COLUMN free_text TEXT",
        "item_damage_type": "ALTER TABLE incident ADD COLUMN item_damage_type VARCHAR",
        "type_id": "ALTER TABLE incident ADD COLUMN type_id INTEGER",
        "modifiers": "ALTER TABLE incident ADD COLUMN modifiers TEXT",
        "classify_confidence": "ALTER TABLE incident ADD COLUMN classify_confidence FLOAT",
        "question_stage": "ALTER TABLE incident ADD COLUMN question_stage INTEGER DEFAULT 0",
    },
    "analysis_finding": {
        "coverage_amount": "ALTER TABLE analysis_finding ADD COLUMN coverage_amount VARCHAR",
        "plan_amount": "ALTER TABLE analysis_finding ADD COLUMN plan_amount VARCHAR",
    },
    "user_policy": {
        "plan_name": "ALTER TABLE user_policy ADD COLUMN plan_name VARCHAR",
        "subscriber_age": "ALTER TABLE user_policy ADD COLUMN subscriber_age INTEGER",
    },
    "incident_type": {
        "needs_review": "ALTER TABLE incident_type ADD COLUMN needs_review BOOLEAN DEFAULT 0",
    },
    "question_bank": {
        "applies_to_l1": "ALTER TABLE question_bank ADD COLUMN applies_to_l1 VARCHAR",
        "incident_id": "ALTER TABLE question_bank ADD COLUMN incident_id INTEGER",
        "applies_to_l2": "ALTER TABLE question_bank ADD COLUMN applies_to_l2 VARCHAR",
        "stage": "ALTER TABLE question_bank ADD COLUMN stage VARCHAR",
        "answer_type": "ALTER TABLE question_bank ADD COLUMN answer_type VARCHAR DEFAULT 'text'",
    },
    "overlap_rule": {
        "anchor_phrase": "ALTER TABLE overlap_rule ADD COLUMN anchor_phrase VARCHAR",
    },
    "insurer_premium": {
        "period_days": "ALTER TABLE insurer_premium ADD COLUMN period_days INTEGER DEFAULT 7 NOT NULL",
    },
}


def _add_missing_columns(engine, table: str, additions: dict[str, str]) -> None:
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        for col, ddl in additions.items():
            if col not in existing:
                conn.execute(text(ddl))
        conn.commit()


def _migrate_insurer_premium_to_plan_schema(engine) -> None:
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


def apply(engine) -> None:
    """이 engine이 가리키는 DB의 스키마를 모델에 맞춘다. 몇 번을 돌려도 결과가 같다."""
    Base.metadata.create_all(bind=engine)
    for table, additions in _COLUMN_ADDITIONS.items():
        _add_missing_columns(engine, table, additions)
    _migrate_insurer_premium_to_plan_schema(engine)
