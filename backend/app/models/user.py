"""영역 B: 사용자 도메인 (new.md 참조)"""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
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
    # 한 번 입력한 나이를 프로필에 저장해두고 자동으로 채워 넣는다.
    age = Column(Integer, nullable=True)

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

    user = relationship("AppUser", back_populates="trips")


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

    user = relationship("AppUser", back_populates="incidents")
    incident_type = relationship("IncidentType")
    evidences = relationship("Evidence", back_populates="incident")
    user_policy = relationship("UserPolicy")


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incident.incident_id"), nullable=False)
    required_doc_std_id = Column(Integer, ForeignKey("required_doc_std.required_doc_std_id"), nullable=True)
    status = Column(String)  # 보유/미보유/발급불가
    memo = Column(Text)

    incident = relationship("Incident", back_populates="evidences")
    required_doc_std = relationship("RequiredDocStd")
