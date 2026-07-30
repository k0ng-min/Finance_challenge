"""영역 A: 약관 지식베이스 (new.md 참조)"""
from sqlalchemy import (
    Boolean, Column, Date, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


class Insurer(Base):
    __tablename__ = "insurer"

    insurer_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    is_underwriter = Column(Boolean, default=True)
    official_url = Column(String)

    products = relationship("Product", back_populates="insurer")


class Product(Base):
    __tablename__ = "product"

    product_id = Column(Integer, primary_key=True)
    insurer_id = Column(Integer, ForeignKey("insurer.insurer_id"), nullable=False)
    name = Column(String, nullable=False)
    product_code = Column(String)
    channel = Column(String)
    sale_start = Column(Date)
    sale_end = Column(Date)
    collected_at = Column(Date)
    review_status = Column(String, default="raw")  # raw/verified

    insurer = relationship("Insurer", back_populates="products")
    policy_versions = relationship("PolicyVersion", back_populates="product")


class PolicyVersion(Base):
    __tablename__ = "policy_version"

    policy_version_id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product.product_id"), nullable=False)
    version_label = Column(String, nullable=False)
    effective_date = Column(Date)
    approval_no = Column(String)
    source_url = Column(String)
    file_hash = Column(String)

    product = relationship("Product", back_populates="policy_versions")
    coverages = relationship("Coverage", back_populates="policy_version")
    clauses = relationship("Clause", back_populates="policy_version")


class CoverageStd(Base):
    __tablename__ = "coverage_std"

    coverage_std_id = Column(Integer, primary_key=True)
    std_code = Column(String, unique=True, nullable=False)
    std_name = Column(String, nullable=False)
    category = Column(String)
    is_base = Column(Boolean, default=False)  # True=보통약관(기본), False=특별약관

    coverages = relationship("Coverage", back_populates="coverage_std")


class Coverage(Base):
    __tablename__ = "coverage"

    coverage_id = Column(Integer, primary_key=True)
    policy_version_id = Column(Integer, ForeignKey("policy_version.policy_version_id"), nullable=False)
    coverage_std_id = Column(Integer, ForeignKey("coverage_std.coverage_std_id"), nullable=True)
    raw_name = Column(String, nullable=False)
    definition = Column(Text)
    limit_amount = Column(String)
    deductible = Column(String)
    waiting_condition = Column(String)

    policy_version = relationship("PolicyVersion", back_populates="coverages")
    coverage_std = relationship("CoverageStd", back_populates="coverages")
    clauses = relationship("Clause", back_populates="coverage")
    doc_links = relationship("CoverageDocMap", back_populates="coverage")


class Clause(Base):
    __tablename__ = "clause"

    clause_id = Column(Integer, primary_key=True)
    policy_version_id = Column(Integer, ForeignKey("policy_version.policy_version_id"), nullable=False)
    coverage_id = Column(Integer, ForeignKey("coverage.coverage_id"), nullable=True)
    clause_type = Column(String)  # 보장정의/면책/제한/조건/서류/공통
    article_no = Column(String)
    text = Column(Text, nullable=False)
    page_ref = Column(String)
    embedding_id = Column(String)
    default_color = Column(String)  # 파랑/초록/노랑/빨강/회색
    highlight_spans = Column(Text, nullable=True)  # Gemini가 나눈 인라인 색상 구간 캐시 (JSON)
    plain_text = Column(Text, nullable=True)  # Gemini가 풀어쓴 쉬운말 설명 캐시

    policy_version = relationship("PolicyVersion", back_populates="clauses")
    coverage = relationship("Coverage", back_populates="clauses")


class RequiredDocStd(Base):
    __tablename__ = "required_doc_std"

    required_doc_std_id = Column(Integer, primary_key=True)
    doc_code = Column(String, unique=True, nullable=False)
    doc_name = Column(String, nullable=False)
    acquire_location = Column(String)  # 현지only/귀국가능/공통
    note = Column(Text)

    coverage_links = relationship("CoverageDocMap", back_populates="required_doc_std")


class CoverageDocMap(Base):
    __tablename__ = "coverage_doc_map"

    coverage_doc_id = Column(Integer, primary_key=True)
    coverage_id = Column(Integer, ForeignKey("coverage.coverage_id"), nullable=False)
    required_doc_std_id = Column(Integer, ForeignKey("required_doc_std.required_doc_std_id"), nullable=False)
    is_mandatory = Column(Boolean, default=True)
    clause_id = Column(Integer, ForeignKey("clause.clause_id"), nullable=True)

    coverage = relationship("Coverage", back_populates="doc_links")
    required_doc_std = relationship("RequiredDocStd", back_populates="coverage_links")
    clause = relationship("Clause")
