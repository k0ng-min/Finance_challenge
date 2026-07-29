from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import AppUser

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    nickname: str = "guest"


class UserOut(BaseModel):
    user_id: int
    nickname: str

    class Config:
        from_attributes = True


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """개인정보 최소수집 원칙(ne.md 14)에 따라 닉네임만 받는다."""
    user = AppUser(nickname=payload.nickname)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
