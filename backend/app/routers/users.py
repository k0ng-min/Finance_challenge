import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import AppUser, Trip, Incident, UserPremiumWatchlist
from app.limiter import limiter
from app.routers.auth import get_current_user_optional, verify_owner
from app.services.auth import issue_session

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    nickname: str = "guest"


class UserOut(BaseModel):
    user_id: int
    nickname: str
    # 게스트도 이 토큰으로 본인을 증명한다. 예전에는 토큰 없이 user_id만으로 조회가 돼서,
    # 순차 정수인 user_id를 훑으면 남의 여행·보험·사고를 전부 볼 수 있었다.
    token: str


class TripSummaryOut(BaseModel):
    trip_id: int
    destination: str | None
    start_date: str | None
    end_date: str | None
    risk_level: str | None
    # 이 여행에 대해 등록해 둔 보험. 사고 접수 화면은 보험을 먼저 고르고 여행을 고르는데,
    # 이 값이 없으면 "지금 고른 보험의 여행"을 가려낼 수 없어 다른 보험으로 등록한 여행까지
    # 같이 보였다. 아직 보험을 붙이지 않은 여행은 None이며, 어느 보험을 골라도 보인다.
    user_policy_id: int | None = None


class IncidentSummaryOut(BaseModel):
    incident_id: int
    country: str | None
    occurred_at: str | None
    diagnosis: str | None
    cause: str | None
    user_policy_id: int | None = None
    linked_insurer_code: str | None = None
    linked_insurer_name: str | None = None


class PremiumWatchlistIn(BaseModel):
    insurer_codes: list[str]


class PremiumWatchlistOut(BaseModel):
    insurer_codes: list[str]


@router.post("", response_model=UserOut)
@limiter.limit("30/hour")
def create_user(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """개인정보 최소수집 원칙에 따라 닉네임만 받는다.

    세션 토큰을 함께 발급한다 — 게스트도 본인 데이터를 다시 꺼내려면 소유권을 증명해야
    하기 때문이다. 계정을 무제한으로 찍어내지 못하도록 생성 자체에도 한도를 둔다.
    """
    user = AppUser(nickname=payload.nickname)
    token = issue_session(user)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(user_id=user.user_id, nickname=user.nickname, token=token)


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
            user_policy_id=t.user_policy_id,
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


@router.get("/{user_id}/premium-watchlist", response_model=PremiumWatchlistOut)
def get_premium_watchlist(
    user_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """보험료 비교(PremiumCalc)에서 담아 둔 보험사 목록("비교함"). 게스트는 서버에 저장하지
    않으므로(로그인해야만 나중에 다시 찾을 수 있다) 로그인 계정만 부를 수 있다."""
    verify_owner(user_id, current)
    rows = (
        db.query(UserPremiumWatchlist)
        .filter(UserPremiumWatchlist.user_id == user_id)
        .all()
    )
    return PremiumWatchlistOut(insurer_codes=[r.insurer_code for r in rows])


@router.put("/{user_id}/premium-watchlist", response_model=PremiumWatchlistOut)
def set_premium_watchlist(
    user_id: int, payload: PremiumWatchlistIn, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """비교함 전체를 통째로 갈아끼운다(추가/삭제를 화면에서 미리 합친 최종 목록을 그대로
    받는다) — 항목 하나하나를 추가/삭제 API로 나누면 화면 쪽 상태와 서버 쪽 상태가
    어긋날 여지가 생긴다."""
    verify_owner(user_id, current)
    db.query(UserPremiumWatchlist).filter(UserPremiumWatchlist.user_id == user_id) \
        .delete(synchronize_session=False)
    seen: set[str] = set()
    for code in payload.insurer_codes:
        code = code.upper().strip()
        if not code or code in seen:
            continue
        seen.add(code)
        db.add(UserPremiumWatchlist(user_id=user_id, insurer_code=code))
    db.commit()
    return PremiumWatchlistOut(insurer_codes=sorted(seen))
