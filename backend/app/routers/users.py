import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import AppUser, Trip, Incident
from app.routers.auth import get_current_user_optional, verify_owner

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    nickname: str = "guest"


class UserOut(BaseModel):
    user_id: int
    nickname: str

    class Config:
        from_attributes = True


class TripSummaryOut(BaseModel):
    trip_id: int
    destination: str | None
    start_date: str | None
    end_date: str | None
    risk_level: str | None


class IncidentSummaryOut(BaseModel):
    incident_id: int
    country: str | None
    occurred_at: str | None
    diagnosis: str | None
    cause: str | None
    user_policy_id: int | None = None
    linked_insurer_code: str | None = None
    linked_insurer_name: str | None = None


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """개인정보 최소수집 원칙(ne.md 14)에 따라 닉네임만 받는다."""
    user = AppUser(nickname=payload.nickname)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/trips", response_model=list[TripSummaryOut])
def list_trips(
    user_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """로그인 계정에서 예전에 만든 여행 기록들을 다시 볼 수 있게 목록으로 준다."""
    verify_owner(user_id, current)
    trips = (
        db.query(Trip)
        .filter(Trip.user_id == user_id)
        .order_by(Trip.trip_id.desc())
        .all()
    )
    out = []
    for t in trips:
        risk_level = None
        if t.risk_profile:
            try:
                risk_level = json.loads(t.risk_profile).get("risk_level")
            except (json.JSONDecodeError, AttributeError):
                pass
        out.append(TripSummaryOut(
            trip_id=t.trip_id,
            destination=t.destination,
            start_date=t.start_date.isoformat() if t.start_date else None,
            end_date=t.end_date.isoformat() if t.end_date else None,
            risk_level=risk_level,
        ))
    return out


@router.get("/{user_id}/incidents", response_model=list[IncidentSummaryOut])
def list_incidents(
    user_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """로그인 계정에서 예전에 접수한 사고들을 다시 볼 수 있게 목록으로 준다."""
    verify_owner(user_id, current)
    incidents = (
        db.query(Incident)
        .filter(Incident.user_id == user_id)
        .order_by(Incident.incident_id.desc())
        .all()
    )
    out = []
    for i in incidents:
        linked_insurer_code = None
        linked_insurer_name = None
        if i.user_policy:
            linked_insurer_code = i.user_policy.product.insurer.code if i.user_policy.product else None
            linked_insurer_name = (
                i.user_policy.product.insurer.name if i.user_policy.product else i.user_policy.insurer_name_raw
            )
        out.append(IncidentSummaryOut(
            incident_id=i.incident_id,
            country=i.country,
            occurred_at=i.occurred_at.isoformat() if i.occurred_at else None,
            diagnosis=i.diagnosis,
            cause=i.cause,
            user_policy_id=i.user_policy_id,
            linked_insurer_code=linked_insurer_code,
            linked_insurer_name=linked_insurer_name,
        ))
    return out
