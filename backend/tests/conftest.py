"""테스트는 운영 DB(data/app.db)를 절대 건드리지 않는다 — 인메모리 SQLite를 새로 만들어 쓴다."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models  # noqa: F401  (모델 등록을 위해 import)


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
