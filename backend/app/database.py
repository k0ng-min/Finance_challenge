import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 기본값은 저장소에 커밋된 약관 KB 파일이다. 환경변수로 바꿀 수 있게 열어 두는 이유가 있다 —
# 이 경로가 상수로 박혀 있는 동안에는 "이 앱을 다른 DB로 띄운다"는 방법 자체가 없어서,
# 로컬에서 화면을 눌러 보거나 app.main을 import하는 테스트를 돌리기만 해도 게스트 계정·여행·
# 사고 행이 전부 커밋 대상 파일에 쌓였다(reset_guest_data.py가 배포 전마다 지우고 있는 그
# 흔적이 바로 이것이다). QA용으로 띄울 때는 사본을 가리키면 된다:
#
#     DATABASE_URL="sqlite:///./data/qa.db" uvicorn app.main:app
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
