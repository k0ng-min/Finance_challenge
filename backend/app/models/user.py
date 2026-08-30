"""영역 B: 사용자 도메인 (new.md 참조)"""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AppUser(Base):
    __tablename__ = "app_user"

    user_id = Column(Integer, primary_key=True)
    nickname = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    # 인증 관련 (게스트로 시작했다가 이메일 가입 시 같은 계정에 이메일·비밀번호만 붙는다 —
    # 게스트로 쌓은 여행/보험 데이터를 그대로 이어받기 위함)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    password_salt = Column(String, nullable=True)
    auth_provider = Column(String, default="guest")  # guest/email/kakao/google
    session_token = Column(String, unique=True, nullable=True)
    session_expires_at = Column(DateTime, nullable=True)
    kakao_id = Column(String, unique=True, nullable=True)
    google_id = Column(String, unique=True, nullable=True)

    # 개인정보보호법상 회원가입 동의 기록 — 각 항목에 실제로 동의한 시각을 남긴다
    # (동의 안 함 = NULL). 마케팅은 선택 동의라 없어도 가입 자체는 막지 않는다.
    terms_agreed_at = Column(DateTime, nullable=True)
    privacy_agreed_at = Column(DateTime, nullable=True)
    marketing_agreed_at = Column(DateTime, nullable=True)
    # 여행 준비·사고 접수·내 보험 등록에서 매번 다시 물어보지 않도록, 로그인 계정에는
    # 한 번 입력한 나이·성별을 프로필에 저장해두고 자동으로 채워 넣는다.
    # 성별은 보험료가 나이와 함께 성별로도 갈리기 때문에 같이 받는다("M"/"F").
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)

    # --- 로그인 보호 ---------------------------------------------------------
    # 요청 빈도 제한(slowapi)만으로는 대입 공격을 못 막는다. 그 한도는 토큰이나 IP 단위라
    # 공격자가 주소를 바꿔 가며 같은 계정을 계속 두드리면 그대로 통과한다. 그래서 계정
    # 자체에도 연속 실패를 세어 두고, 일정 횟수를 넘기면 잠시 잠근다(금융권에서 쓰는 방식).
    failed_login_count = Column(Integer, default=0, nullable=True)
    #: 이 시각까지는 비밀번호가 맞아도 로그인을 받지 않는다. 성공하면 지워진다.
    locked_until = Column(DateTime, nullable=True)
    #: 마지막으로 이 계정 토큰이 실제로 쓰인 시각. 유휴 세션 만료 판정에 쓴다.
    last_seen_at = Column(DateTime, nullable=True)

    trips = relationship("Trip", back_populates="user")
    policies = relationship("UserPolicy", back_populates="user")
    incidents = relationship("Incident", back_populates="user")


class Trip(Base):
    __tablename__ = "trip"

    trip_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("app_user.user_id"), nullable=False)
    destination = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    purpose = Column(String)
    activities = Column(Text)  # JSON
    companion_type = Column(String)
    rental_car = Column(Boolean, default=False)
    risk_profile = Column(Text)  # JSON
    coverage_priority = Column(Text)  # JSON
    # 이 여행에 대해 실제로 등록한 보험. 여행과 보험을 한 묶음으로 들고 있어야 나중에 사고를
    # 접수할 때 "어느 여행의 어느 보험으로 청구하는지"가 자동으로 이어진다.
    user_policy_id = Column(Integer, ForeignKey("user_policy.user_policy_id"), nullable=True)

    user = relationship("AppUser", back_populates="trips")
    user_policy = relationship("UserPolicy", foreign_keys=[user_policy_id])


class UserPolicy(Base):
    __tablename__ = "user_policy"

    user_policy_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("app_user.user_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.product_id"), nullable=True)
    policy_version_id = Column(Integer, ForeignKey("policy_version.policy_version_id"), nullable=True)
    insurer_name_raw = Column(String)
    product_name_raw = Column(String)
    policy_type = Column(String)  # 직접가입/카드부가/단체 — 더 이상 등록 화면에서 받지 않음(과거 데이터 호환용으로만 남김)
    subscriber_age = Column(Integer, nullable=True)  # 가입자 나이
    # 그 보험사가 실제로 파는 등급명 그대로(예: "표준형") — 보험사 순위·보험료 화면에서
    # 등급을 고르고 등록하면 여기 남는다. 담보 목록(UserCoverage)은 여전히 policy_version의
    # 실제 약관(Coverage)에서 채우므로 이 값이 담보 목록 자체를 바꾸지는 않는다 — 어느
    # 등급을 염두에 두고 등록했는지 기록해 사고 접수·보관함 화면에 참고로 보여줄 뿐이다.
    plan_name = Column(String, nullable=True)
    period_start = Column(Date)
    period_end = Column(Date)

    user = relationship("AppUser", back_populates="policies")
    coverages = relationship("UserCoverage", back_populates="user_policy")
    product = relationship("Product")
    policy_version = relationship("PolicyVersion")


class UserCoverage(Base):
    __tablename__ = "user_coverage"

    user_coverage_id = Column(Integer, primary_key=True)
    user_policy_id = Column(Integer, ForeignKey("user_policy.user_policy_id"), nullable=False)
    coverage_id = Column(Integer, ForeignKey("coverage.coverage_id"), nullable=True)
    coverage_std_id = Column(Integer, ForeignKey("coverage_std.coverage_std_id"), nullable=True)
    raw_name = Column(String)
    subscribed_amount = Column(String)

    user_policy = relationship("UserPolicy", back_populates="coverages")
    coverage = relationship("Coverage")
    coverage_std = relationship("CoverageStd")


class Incident(Base):
    __tablename__ = "incident"

    incident_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("app_user.user_id"), nullable=False)
    trip_id = Column(Integer, ForeignKey("trip.trip_id"), nullable=True)
    user_policy_id = Column(Integer, ForeignKey("user_policy.user_policy_id"), nullable=True)
    country = Column(String)
    occurred_at = Column(DateTime)
    cause = Column(String)
    injury_part = Column(String)
    diagnosis = Column(String)
    # 기본값을 두지 않는다: None(아직 모름)과 False(확인된 '아니오')를 구분해야
    # 능동 질문 엔진이 "이미 확인된 사실"을 중복으로 다시 묻지 않는다.
    hospitalized = Column(Boolean, nullable=True)
    surgery = Column(Boolean, nullable=True)
    local_treatment = Column(Boolean, nullable=True)
    medical_cost = Column(String)
    returned_home = Column(Boolean, nullable=True)
    structured = Column(Text)  # JSON, LLM 구조화 결과
    # 원문 자유서술 사고 설명 — 재조회 시 분실/도난형 사고 여부를 다시 판별하는 데 쓴다
    # (Gemini를 또 부르지 않고 키워드로만 재판별하므로 저장해둔 원문이 필요하다).
    free_text = Column(Text)
    # "도난"|"파손"|"분실" — 휴대품손해 특약이 분실은 보상하지 않고 도난/파손만 보상하므로 구분한다.
    item_damage_type = Column(String, nullable=True)
    # 사고유형 분류 결과(incident_type 2단계 사전). item_damage_type 같은 담보별 임시
    # 플래그를 대체해 나가기 위한 정식 축. app.services.incident_classify_gemini가 채우고,
    # app.services.claim_review가 이 값을 기준으로 담보를 찾는다(routers/incidents.py 참고).
    type_id = Column(Integer, ForeignKey("incident_type.type_id"), nullable=True)
    # 수식자 축(활동/장소/시점/상태/대상) JSON — 같은 사고유형이라도 조항 적용이 갈리는
    # 부가 정보(예: 활동=스쿠버다이빙 → 상해 면책 조항 검토)를 유형과 분리해서 담는다.
    modifiers = Column(Text, nullable=True)
    classify_confidence = Column(Float, nullable=True)
    # 이 사고에 대해 맞춤 질문 생성(incident_questions_gemini)을 한 번이라도 끝냈는지.
    # "만들어진 질문이 0건"과 "아직 만들어 본 적 없음"을 구분하기 위한 것이다 — 전자는
    # 모델이 "더 물을 게 없다"고 판단한 결과라 공용 뱅크를 다시 열면 안 되고, 후자는
    # (Gemini가 없는 환경 등) 공용 뱅크가 유일한 질문 출처다.
    # 사고 접수 질문이 어디까지 진행됐는지. 0=아직 안 만듦, 1=대분류 질문을 만듦,
    # 2=세부분류 질문까지 만듦. 만든 질문이 0건이어도 단계는 올라간다 — "만들었는데
    # 물을 게 없었다"와 "아직 안 만들었다"를 구분해야 재방문 때 질문이 되살아나지 않는다.
    question_stage = Column(Integer, default=0)

    user = relationship("AppUser", back_populates="incidents")
    incident_type = relationship("IncidentType")
    evidences = relationship("Evidence", back_populates="incident")
    user_policy = relationship("UserPolicy")
    trip = relationship("Trip")


class UserPremiumWatchlist(Base):
    """로그인 계정이 보험료 비교(PremiumCalc)에서 담아 둔 보험사 목록("비교함").

    게스트는 이 표에 저장하지 않는다 — 이 앱은 로그인 없는 게스트도 모든 기능을 쓸 수
    있는 게 기본 설계지만, 게스트는 user_id가 브라우저를 벗어나면 이어지지 않으므로
    서버에 남겨봐야 다시 못 찾는다(다른 데이터도 전부 이 원칙을 따른다). 그래서 이
    목록은 화면의 selected 상태로만 갖고 있다가, 로그인 계정일 때만 서버에 동기화한다.
    """
    __tablename__ = "user_premium_watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "insurer_code", name="uq_watchlist_user_insurer"),
    )

    watchlist_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("app_user.user_id"), nullable=False)
    insurer_code = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incident.incident_id"), nullable=False)
    required_doc_std_id = Column(Integer, ForeignKey("required_doc_std.required_doc_std_id"), nullable=True)
    status = Column(String)  # 보유/미보유/발급불가
    memo = Column(Text)

    incident = relationship("Incident", back_populates="evidences")
    required_doc_std = relationship("RequiredDocStd")


class SecurityEvent(Base):
    """보안과 관련된 사건만 따로 남기는 감사 로그.

    로그인 성공·실패, 계정 잠금, 남의 데이터 접근 시도, 비밀번호 변경, 계정 삭제처럼
    "누가 언제 무엇을 시도했는가"가 사후에 확인돼야 하는 일들이 지금까지 아무 데도
    남지 않았다. 금융 분야에서 이런 기록은 사고가 났을 때 경위를 밝힐 유일한 근거라
    별도 표로 둔다 — 애플리케이션 로그와 달리 재배포로 사라지지 않아야 한다.

    남기지 않는 것을 분명히 해 둔다. 비밀번호와 세션 토큰은 원문도 해시도 넣지 않고,
    사고 내용·진단명 같은 민감정보도 넣지 않는다. 감사 로그가 유출되면 그것 자체가
    2차 사고가 되기 때문이다. 주체는 user_id로만 가리키고, 접속 주소는 원문 대신
    해시 앞자리만 남겨 "같은 곳에서 반복된 시도"는 셀 수 있되 주소 자체는 복원되지 않게 한다.
    """

    __tablename__ = "security_event"

    security_event_id = Column(Integer, primary_key=True)
    occurred_at = Column(DateTime, server_default=func.now(), index=True)
    #: "login_success" 같은 사건 종류. app.services.security_audit에 목록이 있다.
    event_type = Column(String, nullable=False, index=True)
    #: 사건의 주체. 계정을 특정할 수 없는 실패(없는 이메일로 로그인 시도)는 NULL이다.
    user_id = Column(Integer, ForeignKey("app_user.user_id"), nullable=True, index=True)
    #: 접속 주소의 SHA-256 앞 16자리. 원문 주소는 남기지 않는다.
    client_hash = Column(String, nullable=True)
    #: 어떤 경로에서 벌어진 일인지(예: "POST /auth/login").
    target = Column(String, nullable=True)
    #: 사람이 읽을 한 줄. 개인정보·자격증명은 담지 않는다.
    detail = Column(String, nullable=True)
