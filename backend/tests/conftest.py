"""테스트는 운영 DB(data/app.db)를 절대 건드리지 않는다 — 인메모리 SQLite를 새로 만들어 쓴다."""
import os
import pathlib
import shutil
import tempfile

# 이 설정은 아래 app.* import보다 먼저 있어야 한다.
#
# 테스트는 전부 get_db를 자기 세션으로 갈아끼우므로 "운영 DB를 안 건드린다"는 약속이
# 지켜지는 듯 보였지만, 실제로는 새고 있었다. app.main을 import하는 것만으로 그 모듈
# 최상위의 스키마 마이그레이션과 시드가 돌고, 그것들은 dependency_overrides가 아니라
# app.database.engine을 직접 쓴다 — 즉 커밋 대상인 data/app.db에 그대로 쓰였다.
# (reset_guest_data.py가 배포 전마다 지우던 흔적의 출처 중 하나가 이것이다.)
# 그 부작용까지 임시 파일로 돌려 버린다.
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{(pathlib.Path(tempfile.mkdtemp(prefix='pytest-appdb-')) / 'side-effects.db').as_posix()}",
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import schema_migrations
from app.database import Base
from app import models  # noqa: F401  (모델 등록을 위해 import)


@pytest.fixture
def kb_session(tmp_path):
    """실제 약관 지식베이스가 들어있는 세션.

    E2E는 조항·담보·사고유형이 실제로 적재돼 있어야 의미가 있어서 빈 인메모리 DB로는
    못 한다. 그렇다고 운영 DB(data/app.db)를 직접 열면 테스트가 사용자·여행 행을 남긴다.
    파일을 통째로 복사해서 그 사본에만 쓰고 테스트가 끝나면 tmp_path와 함께 사라진다.
    """
    source = pathlib.Path(__file__).resolve().parents[1] / "data" / "app.db"
    if not source.exists():
        pytest.skip("약관 KB(data/app.db)가 없어 E2E를 건너뜁니다")

    copy = tmp_path / "kb.db"
    shutil.copyfile(source, copy)

    engine = create_engine(f"sqlite:///{copy.as_posix()}", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    # 커밋된 app.db는 그때그때의 스키마로 굳어 있다. create_all은 없는 '테이블'만 만들 뿐
    # 기존 테이블에 '컬럼'을 붙이지 않으므로, 모델에 컬럼이 하나 늘면 이 사본에서만 깨진다.
    # 앱이 기동 때 하는 것과 똑같은 맞추기를 여기서도 한 번 돌린다.
    schema_migrations.apply(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 인메모리 DB는 연결이 끊기면 사라지므로 연결을 하나로 고정한다
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
