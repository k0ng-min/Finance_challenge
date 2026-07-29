"""영역 B: 사용자 도메인 (new.md 참조)"""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AppUser(Base):
    __tablename__ = "app_user"

    user_id = Column(Integer, primary_key=True)
    nickname = Column(String)
    created_at = Column(DateTime, server_default=func.now())

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
    policy_type = Column(String)  # 직접가입/카드부가/단체
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

    user = relationship("AppUser", back_populates="incidents")
    evidences = relationship("Evidence", back_populates="incident")


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incident.incident_id"), nullable=False)
    required_doc_std_id = Column(Integer, ForeignKey("required_doc_std.required_doc_std_id"), nullable=True)
    status = Column(String)  # 보유/미보유/발급불가
    memo = Column(Text)

    incident = relationship("Incident", back_populates="evidences")
    required_doc_std = relationship("RequiredDocStd")
