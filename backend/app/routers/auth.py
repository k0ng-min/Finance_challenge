
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.limiter import limiter
from app.models.user import AppUser, Incident
from app.services.auth import (
    hash_password, hash_session_token, issue_session, session_expiry, utc_now, verify_password,
)
from app.services.deletion import delete_user_cascade, wipe_user_data
from app.services.oauth import exchange_kakao_code, exchange_google_code

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupIn(BaseModel):
    email: str
    password: str
    nickname: str = "여행자"
    user_id: int | None = None  # 이미 게스트로 쌓아둔 데이터가 있으면 그 계정에 이메일을 붙인다
    # 개인정보보호법상 필수 동의 3종 + 선택 동의 1종. 필수 항목이 하나라도 빠지면 가입을 막는다.
    agree_terms: bool = False
    agree_privacy: bool = False
    agree_age14: bool = False
    agree_marketing: bool = False


class LoginIn(BaseModel):
    email: str
    password: str


class PasswordSetIn(BaseModel):
    """소셜(카카오·구글)로 가입한 계정에 이메일 로그인용 비밀번호를 새로 정하거나 바꾼다."""
    new_password: str
    current_password: str | None = None  # 이미 비밀번호가 있으면 확인용으로 받는다


class ConsentIn(BaseModel):
    agree_terms: bool = False
    agree_privacy: bool = False
    agree_marketing: bool = False


class OAuthIn(BaseModel):
    code: str
    user_id: int | None = None  # 이미 게스트로 쌓아둔 데이터가 있으면 그 계정을 그대로 승격시킨다
    intent: str = "login"  # "login"이면 미가입 계정을 거부하고, "signup"일 때만 새 계정을 만든다


class AuthUserOut(BaseModel):
    user_id: int
    nickname: str
    email: str | None
    auth_provider: str
    token: str
    age: int | None = None
    sex: str | None = None
    is_new_user: bool = False
    # 가입 마지막 단계(닉네임·나이·필수동의)를 실제로 마쳤는지. 소셜 로그인은 콜백에서
    # 계정 행이 먼저 만들어지므로, 이 값이 False면 프론트가 어디에 있든 그 화면으로
    # 되돌린다 — 중간에 뒤로 나가서 "계정은 있는데 프로필이 빈" 상태로 남지 않게 한다.
    signup_completed: bool = True
    # 이메일+비밀번호로도 로그인할 수 있게 비밀번호를 설정해 뒀는지(계정 화면 표시용).
    has_password: bool = False

    class Config:
        from_attributes = True


class NicknameIn(BaseModel):
    nickname: str


class AgeIn(BaseModel):
    age: int


class SexIn(BaseModel):
    sex: str


class ProviderStatusOut(BaseModel):
    kakao_enabled: bool
    google_enabled: bool
    kakao_client_id: str
    google_client_id: str
    kakao_redirect_uri: str
    google_redirect_uri: str


def signup_completed(user: AppUser) -> bool:
    """가입 마지막 단계(닉네임·나이·필수동의)를 마쳤는지.

    소셜 로그인은 인가 코드를 받는 순간 계정 행을 먼저 만들어야 세션을 줄 수 있어서,
    "계정은 생겼는데 프로필은 비어 있는" 중간 상태가 반드시 한 번 생긴다. 예전에는 그
    상태에서 뒤로 나가버리면 계정만 덩그러니 남고, 다시 로그인해도 프로필을 채울 화면이
    없어서 영영 빈 계정이 됐다. 필수 동의 시각(terms_agreed_at)을 "가입 완료" 표시로 삼아
    프론트가 그 화면으로 다시 데려가게 한다.
    """
    return user.terms_agreed_at is not None


def auth_user_out(user: AppUser, *, is_new: bool = False) -> "AuthUserOut":
    return AuthUserOut(
        user_id=user.user_id, nickname=user.nickname, email=user.email,
        auth_provider=user.auth_provider, token=user.raw_session_token,
        age=user.age, sex=user.sex, is_new_user=is_new,
        signup_completed=signup_completed(user),
        has_password=bool(user.password_hash),
    )


def _login_or_upgrade(db: Session, *, id_column, provider_id: str, email: str | None,
                       nickname: str, provider: str, guest_user_id: int | None,
                       intent: str = "login") -> tuple[AppUser, bool]:
    """제공자 ID로 기존 계정을 찾고, 없으면 게스트 계정을 승격하거나 새로 만든다.
    (사용자, 이번에 새로 만들어진 계정인지) 튜플을 반환한다 — 신규 가입이면 프론트가
    닉네임 설정 화면을 한 번 보여줄 수 있게 하기 위함.
    intent="login"인데 해당 계정이 아직 없으면(=가입한 적 없음) 새로 만들지 않고 거부한다 —
    "로그인" 버튼을 눌렀는데 모르는 사이에 회원가입이 되어버리는 걸 막기 위함."""
    existing = db.query(AppUser).filter(id_column == provider_id).first()
    if existing:
        existing.raw_session_token = issue_session(existing)
        db.commit()
        return existing, False

    if intent == "login":
        raise HTTPException(status_code=404, detail="아직 가입되지 않은 계정이에요. 먼저 회원가입해주세요.")

    user = None
    if guest_user_id:
        candidate = db.get(AppUser, guest_user_id)
        if candidate and candidate.kakao_id is None and candidate.google_id is None and candidate.email is None:
            user = candidate
            # 로그인 전에 만든 여행·보험·사고는 전부 "체험용" 스크래치 데이터다. 정식 계정
            # 이력에 그대로 딸려오면 내가 등록한 적 없는 여행·사고가 보관함에 들어앉게 되므로,
            # 가입/로그인 순간 깨끗한 이력으로 시작한다.
            wipe_user_data(db, user.user_id)

    if user is None:
        user = AppUser(nickname=nickname)
        db.add(user)

    user.nickname = nickname or user.nickname
    if email:
        user.email = email
    if provider == "kakao":
        user.kakao_id = provider_id
    else:
        user.google_id = provider_id
    user.auth_provider = provider
    user.raw_session_token = issue_session(user)
    db.commit()
    db.refresh(user)
    return user, True


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AppUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    token = authorization.split(" ", 1)[1].strip()
    # DB에는 해시만 있으므로 들어온 토큰을 같은 방식으로 해싱해 대조한다.
    user = db.query(AppUser).filter(AppUser.session_token == hash_session_token(token)).first()
    if not user:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요.")
    if user.session_expires_at and user.session_expires_at < utc_now():
        user.session_token = None
        db.commit()
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요.")
    # DB에는 해시만 있어서 응답에 담을 원문이 없다. 방금 검증한 원문을 실어 보내 응답
    # 빌더들이 그대로 돌려줄 수 있게 한다(새 토큰을 발급하는 게 아니라 있던 것을 되돌려줌).
    user.raw_session_token = token
    return user


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AppUser | None:
    """토큰이 없으면(게스트) None을 준다 — 이 앱은 로그인 없이도 모든 기능을 쓸 수 있는 게
    기본 설계라 여기서 막지 않는다. 토큰이 있는데 무효/만료된 경우엔 그대로 401을 낸다."""
    if not authorization:
        return None
    return get_current_user(authorization=authorization, db=db)


def verify_owner(owner_user_id: int, current: AppUser | None) -> None:
    """URL의 user_id가 요청자 본인인지 확인한다.

    예전에는 토큰이 있을 때만 검사했다. "게스트는 로그인 없이 자기 user_id만 들고 쓰는
    구조"라는 전제였는데, 그 전제를 서버가 확인할 방법이 없다는 게 문제였다 — 토큰을 빼고
    user_id만 바꿔 부르면 남의 여행·보험·사고가 그대로 나왔고, user_id가 순차 정수라
    1부터 훑으면 전수 수집이 가능했다.

    지금은 게스트도 계정 생성 시 세션 토큰을 받으므로(POST /users), 익명 접근을 허용할
    이유가 없다. 로그인 여부와 무관하게 항상 토큰으로 본인을 증명해야 한다.
    """
    # 게스트도 토큰을 갖고 있으므로, 토큰이 없다는 건 "로그인을 안 했다"가 아니라 브라우저에
    # 저장된 정보가 사라졌다는 뜻이다. 로그인하라고 하면 게스트는 할 수 있는 게 없다.
    if current is None:
        raise HTTPException(status_code=401, detail="정보를 확인할 수 없어요. 페이지를 새로고침한 뒤 다시 시도해 주세요.")
    if current.user_id != owner_user_id:
        raise HTTPException(status_code=403, detail="본인 데이터만 확인할 수 있어요.")


@router.post("/signup", response_model=AuthUserOut)
@limiter.limit("10/hour")
def signup(request: Request, payload: SignupIn):
    """이메일/비밀번호 가입은 더 이상 지원하지 않는다 — 카카오·구글로만 가입할 수 있다
    (비밀번호를 우리 서버에 저장하지 않는 편이 유출 위험이 적다). 엔드포인트 자체는 남겨서
    옛 프론트/클라이언트가 호출해도 무슨 상황인지 알 수 있는 메시지를 준다."""
    raise HTTPException(status_code=403, detail="이메일 회원가입은 지원하지 않아요. 카카오 또는 구글로 가입해주세요.")


@router.post("/login", response_model=AuthUserOut)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginIn, db: Session = Depends(get_db)):
    """이메일 + 비밀번호 로그인.

    가입 자체는 여전히 카카오·구글로만 한다. 이 경로는 그렇게 가입한 계정이 계정 화면에서
    따로 정해 둔 비밀번호로 들어오는 통로다(비밀번호를 처음 만드는 회원가입 경로가 아니다).
    그래서 소셜 연결이 없는 계정은 비밀번호가 있어도 여기로 들어올 수 없다.

    응답 문구는 "이메일이 없음"과 "비밀번호가 틀림"을 구분하지 않는다 — 구분하면 어떤
    이메일이 가입돼 있는지 밖에서 훑을 수 있다. 다만 "이 계정은 아직 비밀번호를 안 정했다"는
    본인이 실제로 소셜 로그인을 통과해야만 알 수 있는 정보가 아니라 안내가 꼭 필요한
    상태라, 그때만 별도 문구를 준다.
    """
    email = (payload.email or "").strip().lower()
    user = db.query(AppUser).filter(func.lower(AppUser.email) == email).first()
    is_social = bool(user and (user.kakao_id or user.google_id))

    if user and is_social and not user.password_hash:
        raise HTTPException(
            status_code=403,
            detail="이 계정은 아직 비밀번호를 정하지 않았어요. 구글 또는 카카오로 로그인한 뒤 계정 화면에서 비밀번호를 설정해 주세요.",
        )
    if not user or not is_social or not verify_password(payload.password, user.password_hash, user.password_salt or ""):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 맞지 않아요.")

    user.raw_session_token = issue_session(user)
    db.commit()
    return auth_user_out(user)


@router.post("/password", response_model=AuthUserOut)
@limiter.limit("10/hour")
def set_password(
    request: Request, payload: PasswordSetIn,
    user: AppUser = Depends(get_current_user), db: Session = Depends(get_db),
):
    """소셜로 가입한 계정에 이메일 로그인용 비밀번호를 정하거나 바꾼다.

    비밀번호만으로 새 계정을 만들 수는 없다(가입 경로는 카카오·구글 하나뿐이다). 이미
    비밀번호가 있으면 현재 비밀번호를 확인한다 — 세션이 탈취됐을 때 조용히 비밀번호가
    바뀌어 계정이 통째로 넘어가는 걸 막기 위함이다.
    """
    if not (user.kakao_id or user.google_id):
        raise HTTPException(status_code=403, detail="구글 또는 카카오로 가입한 계정만 비밀번호를 설정할 수 있어요.")
    if not user.email:
        raise HTTPException(status_code=400, detail="이 계정에는 이메일이 없어서 이메일 로그인을 쓸 수 없어요.")
    if user.password_hash:
        if not payload.current_password or not verify_password(
            payload.current_password, user.password_hash, user.password_salt or ""
        ):
            raise HTTPException(status_code=400, detail="현재 비밀번호가 맞지 않아요.")
    new_password = payload.new_password or ""
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상으로 정해주세요.")
    if len(new_password) > 72:
        raise HTTPException(status_code=400, detail="비밀번호는 72자 이하로 정해주세요.")

    digest, salt = hash_password(new_password)
    user.password_hash = digest
    user.password_salt = salt
    db.commit()
    return auth_user_out(user)


@router.delete("/signup-pending")
def cancel_pending_signup(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """가입 마지막 단계(닉네임·나이·필수동의)를 마치기 전에 되돌아 나갈 때 계정을 지운다.

    소셜 콜백에서 계정 행이 먼저 만들어지는 구조라 이 뒷정리가 없으면 "가입을 끝내지
    않았는데 계정만 남아 있는" 상태가 생긴다. 이미 가입을 마친 계정에는 아무 일도 하지
    않는다 — 실수로 이 경로를 다시 불러도 정상 계정이 사라지면 안 된다."""
    if signup_completed(user):
        return {"status": "kept"}
    delete_user_cascade(db, user)
    db.commit()
    return {"status": "deleted"}


@router.post("/consent", response_model=AuthUserOut)
def submit_consent(payload: ConsentIn, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """카카오·구글로 처음 가입한 사용자용 — 닉네임 설정 화면에서 필수 약관에 동의를 받는다.

    이 동의 시각이 곧 "가입 완료" 표시다(signup_completed). 그래서 갱신된 계정 상태를
    그대로 돌려줘, 프론트가 별도 조회 없이 가입 미완료 리다이렉트를 풀 수 있게 한다."""
    if not (payload.agree_terms and payload.agree_privacy):
        raise HTTPException(status_code=400, detail="이용약관과 개인정보 수집·이용에 동의해야 계속할 수 있어요.")
    now = utc_now()
    user.terms_agreed_at = now
    user.privacy_agreed_at = now
    if payload.agree_marketing:
        user.marketing_agreed_at = now
    db.commit()
    return auth_user_out(user)


@router.post("/logout")
def logout(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user.session_token = None
    db.commit()
    return {"status": "ok"}


@router.get("/me", response_model=AuthUserOut)
@limiter.limit("60/minute")
def me(request: Request, user: AppUser = Depends(get_current_user)):
    return auth_user_out(user)


@router.delete("/me")
@limiter.limit("5/hour")
def delete_account(request: Request, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """회원 탈퇴 — 이 계정과 계정이 만든 모든 여행·사고·보험 기록을 되돌릴 수 없이 삭제한다."""
    delete_user_cascade(db, user)
    db.commit()
    return {"status": "deleted"}


@router.get("/providers", response_model=ProviderStatusOut)
def providers():
    """프론트가 카카오/구글 버튼을 활성화할지, 어떤 client_id로 리다이렉트할지 판단하는 데 쓴다."""
    return ProviderStatusOut(
        kakao_enabled=config.KAKAO_LOGIN_ENABLED,
        google_enabled=config.GOOGLE_LOGIN_ENABLED,
        kakao_client_id=config.KAKAO_REST_API_KEY,
        google_client_id=config.GOOGLE_CLIENT_ID,
        kakao_redirect_uri=config.KAKAO_REDIRECT_URI,
        google_redirect_uri=config.GOOGLE_REDIRECT_URI,
    )


@router.post("/kakao", response_model=AuthUserOut)
@limiter.limit("15/hour")
async def kakao_login(request: Request, payload: OAuthIn, db: Session = Depends(get_db)):
    if not config.KAKAO_LOGIN_ENABLED:
        raise HTTPException(status_code=503, detail="카카오 로그인이 아직 설정되지 않았습니다.")
    info = await exchange_kakao_code(payload.code)
    user, is_new = _login_or_upgrade(
        db, id_column=AppUser.kakao_id, provider_id=info["provider_id"], email=info["email"],
        nickname=info["nickname"], provider="kakao", guest_user_id=payload.user_id, intent=payload.intent,
    )
    return auth_user_out(user, is_new=is_new)


@router.post("/google", response_model=AuthUserOut)
@limiter.limit("15/hour")
async def google_login(request: Request, payload: OAuthIn, db: Session = Depends(get_db)):
    if not config.GOOGLE_LOGIN_ENABLED:
        raise HTTPException(status_code=503, detail="구글 로그인이 아직 설정되지 않았습니다.")
    info = await exchange_google_code(payload.code)
    user, is_new = _login_or_upgrade(
        db, id_column=AppUser.google_id, provider_id=info["provider_id"], email=info["email"],
        nickname=info["nickname"], provider="google", guest_user_id=payload.user_id, intent=payload.intent,
    )
    return auth_user_out(user, is_new=is_new)


@router.patch("/nickname", response_model=AuthUserOut)
def update_nickname(payload: NicknameIn, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    nickname = payload.nickname.strip()
    if not nickname:
        raise HTTPException(status_code=400, detail="닉네임을 입력해주세요.")
    if len(nickname) > 20:
        raise HTTPException(status_code=400, detail="닉네임은 20자 이하로 입력해주세요.")
    user.nickname = nickname
    db.commit()
    return auth_user_out(user)


@router.patch("/sex", response_model=AuthUserOut)
def update_sex(payload: SexIn, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    sex = payload.sex.upper()
    if sex not in ("M", "F"):
        raise HTTPException(status_code=400, detail="성별은 M 또는 F여야 합니다.")
    user.sex = sex
    db.commit()
    return auth_user_out(user)


@router.patch("/age", response_model=AuthUserOut)
def update_age(payload: AgeIn, user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.age < 0 or payload.age > 120:
        raise HTTPException(status_code=400, detail="나이를 0~120 사이로 입력해주세요.")
    user.age = payload.age
    db.commit()
    return auth_user_out(user)
