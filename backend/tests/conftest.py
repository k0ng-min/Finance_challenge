"""테스트는 운영 DB(data/app.db)를 절대 건드리지 않는다 — 인메모리 SQLite를 새로 만들어 쓴다."""
import pathlib
import shutil

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
    Base.metadata.create_all(bind=engine)
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
