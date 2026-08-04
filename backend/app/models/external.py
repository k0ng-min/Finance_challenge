"""기존보험 도메인 — 사용자가 이 서비스 밖에서 이미 들고 있는 보험.

UserPolicy(이번 여행에 든 여행자보험)와는 성격이 달라 테이블을 나눈다. UserPolicy는
우리가 약관을 분석해 둔 6개사 상품에 매칭되지만, 기존보험은 그 밖의 상품이라 매칭 대상이
아니고, 담보도 우리 약관 DB에서 끌어올 수 없다.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ExternalPolicy(Base):
    __tablename__ = "external_policy"

    external_policy_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("app_user.user_id"), nullable=False)
    # manual(사용자가 직접 고름) / mock(연동 시연용) / codef(실연동)
    source = Column(String, nullable=False)
    # MEDICAL_INDEMNITY 실손 / ACCIDENT 상해 / DAILY_LIABILITY 일상생활배상책임 /
    # DRIVER 운전자 / OTHER 그 외
    kind = Column(String, nullable=False)
    # 사용자가 자기 보험사·상품명을 모르는 경우가 흔하다 — 몰라도 등록은 되게 둔다.
    insurer_name_raw = Column(String, nullable=True)
    product_name_raw = Column(String, nullable=True)
    # "YYYY-MM". 실손은 이 값 하나로 세대가 갈리고 세대가 보장구조를 결정한다.
    enrolled_ym = Column(String, nullable=True)
    indemnity_gen = Column(Integer, nullable=True)  # 1~4, 실손만
    # CODEF 원본 응답. 나중에 매핑 규칙이 바뀌어도 재해석할 수 있게 원본을 남긴다.
    raw_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    coverages = relationship(
        "ExternalCoverage", back_populates="external_policy", cascade="all, delete-orphan"
    )


class ExternalCoverage(Base):
    __tablename__ = "external_coverage"

    external_coverage_id = Column(Integer, primary_key=True)
    external_policy_id = Column(
        Integer, ForeignKey("external_policy.external_policy_id"), nullable=False
    )
    coverage_std_id = Column(Integer, ForeignKey("coverage_std.coverage_std_id"), nullable=True)
    raw_name = Column(String)
    subscribed_amount = Column(String, nullable=True)
    # standard_terms(표준약관에서 자동) / user_input / codef / unknown
    # 화면에서 "자동 입력"과 "사용자가 직접 입력"을 구분해 보여줘야 신뢰도를 정직하게 전달할 수 있다.
    amount_source = Column(String, nullable=False, default="unknown")

    external_policy = relationship("ExternalPolicy", back_populates="coverages")
    coverage_std = relationship("CoverageStd")


class OverlapRule(Base):
    """중복 판정 규칙. 판정을 코드에 숨기지 않고 행마다 근거 조항을 물려 시드한다 —
    근거 없는 판정이 구조적으로 불가능해진다."""

    __tablename__ = "overlap_rule"

    rule_id = Column(Integer, primary_key=True)
    external_kind = Column(String, nullable=False)
    coverage_std_id = Column(
        Integer, ForeignKey("coverage_std.coverage_std_id"), nullable=False
    )
    # 같은 담보 안에서도 구간에 따라 판정이 갈린다. 예: 해외발생 질병의료비는 해외 의료기관
    # 구간에선 기존 실손과 안 겹치지만, 국내 의료기관 구간에선 겹친다.
    scope = Column(String, nullable=False, default="전체")
    # NO_OVERLAP / DUPLICATE_PRORATA / DUPLICATE_FIXED / PARTIAL / UNKNOWN
    relation = Column(String, nullable=False)
    # UNKNOWN이 아니면 반드시 있어야 한다(seed_overlap_rules.py가 검증한다).
    clause_id = Column(Integer, ForeignKey("clause.clause_id"), nullable=True)
    note = Column(Text)
    # note가 근거로 삼는 조항 원문 속 핵심 문구. clause.text가 _QUOTE_LIMIT보다 길 때
    # _quote()가 이 문구를 포함하는 창(window)을 잘라내는 데 쓴다 — 없으면 이 문구가 조항
    # 뒷부분에 있을 경우 인용문에서 잘려나가 "형식만 근거, 실질은 없는" 상태가 될 수 있다.
    anchor_phrase = Column(String, nullable=True)

    coverage_std = relationship("CoverageStd")
    clause = relationship("Clause")
