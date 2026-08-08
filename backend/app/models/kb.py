"""영역 A: 약관 지식베이스 (new.md 참조)"""
from sqlalchemy import (
    Boolean, Column, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import backref, relationship

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
    incident_links = relationship("ClauseIncidentMap", back_populates="clause")
    terms = relationship("ClauseTerm", back_populates="clause")


class IncidentType(Base):
    """사고유형 사전(2단계 고정 분류).

    담보(coverage_std) 코드에 사고 판단 로직을 직접 매달면, 담보가 늘어날 때마다
    claim_review.py에 하위 유형 분기가 계속 붙는다(=하위유형 폭발). 그래서 "무슨 일이
    있었나"(사고유형)와 "무슨 담보로 받나"(담보)를 분리하고, 조항을 사고유형에 매핑한다.

    L1은 8개로 고정한다(INJ/ILL/PROP/LIA/TRV/CHG/EMG/SPC). 새 사고 유형이 생기면
    L2로만 늘리고, 어디에도 안 맞으면 SPC_OTHER로 보내서 사람이 나중에 재분류한다
    (조용히 버리지 않는다 — 근거 없는 결과 금지 원칙의 반대편인 '근거 있는데 누락' 방지).
    """

    __tablename__ = "incident_type"

    type_id = Column(Integer, primary_key=True)
    l1_code = Column(String, nullable=False)   # 예: "INJ"
    l2_code = Column(String, nullable=False)   # 예: "INJ_OVERSEAS_TREATMENT" (L1 루트 행은 l1_code와 동일)
    name = Column(String, nullable=False)      # 한글 표시명
    parent_id = Column(Integer, ForeignKey("incident_type.type_id"), nullable=True)  # L1 루트는 None
    is_active = Column(Boolean, default=True)
    # 런타임 중 Gemini가 기존 L2 후보 어디에도 못 맞춰서 새로 만든 행이면 True.
    # 조용히 버리지 않고(=SPC_OTHER 원칙을 8개 L1 전체로 일반화) 사람이 나중에 검수하도록 표시만 해둔다.
    needs_review = Column(Boolean, default=False)

    # remote_side는 backref("parent") 쪽에 둬야 children이 실제로 자식 목록을, parent가
    # 부모 한 건을 돌려준다 — 예전엔 반대로 걸려 있어(children이 부모를, parent가 자식
    # 목록을 반환) 이름과 실제 동작이 정반대였다.
    children = relationship("IncidentType", backref=backref("parent", remote_side=[type_id]))
    clause_links = relationship("ClauseIncidentMap", back_populates="incident_type")


class ClauseIncidentMap(Base):
    """조항 ↔ 사고유형 매핑. 하나의 조항이 여러 사고유형에 걸릴 수 있다.

    relevance:
      직접   — 이 사고유형이면 곧바로 이 조항이 지급/판단 근거가 된다
      조건부 — 추가 요건(사망·N일 이상 입원 등)이 충족될 때만 걸린다
      면책   — 이 사고유형을 명시적으로 보상하지 않는 근거 조항
    mapped_by: rule/llm/human — 어떤 경로로 만들어졌는지(사람 검수 대상 선별용)
    """

    __tablename__ = "clause_incident_map"

    map_id = Column(Integer, primary_key=True)
    clause_id = Column(Integer, ForeignKey("clause.clause_id"), nullable=False)
    type_id = Column(Integer, ForeignKey("incident_type.type_id"), nullable=False)
    relevance = Column(String, nullable=False)   # 직접/조건부/면책
    mapped_by = Column(String, nullable=False)   # rule/llm/human
    confidence = Column(Float, nullable=True)

    clause = relationship("Clause", back_populates="incident_links")
    incident_type = relationship("IncidentType", back_populates="clause_links")


class ClauseTerm(Base):
    """조항에서 뽑아낸 정량 조건(지급한도·자기부담금·면책일수·지연기준시간 등).

    raw_text는 반드시 출처 clause.text의 '문자 그대로의 부분 문자열'이어야 한다.
    (clause_spans_gemini._locate_spans와 같은 원칙 — 원문에 없는 조각은 전부 무효 처리.)
    행을 넣기 전 app.services.kb_seed_common.raw_text_is_grounded()로 검증할 것.
    """

    __tablename__ = "clause_term"

    term_id = Column(Integer, primary_key=True)
    clause_id = Column(Integer, ForeignKey("clause.clause_id"), nullable=False)
    term_type = Column(String, nullable=False)  # 지급한도/자기부담금/면책일수/지연기준시간 ...
    value_num = Column(Float, nullable=True)
    unit = Column(String, nullable=True)        # 원/일/시간/%
    basis = Column(String, nullable=True)       # 실손/정액 ...
    condition_text = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)     # 반드시 clause.text의 부분 문자열
    confidence = Column(Float, nullable=True)

    clause = relationship("Clause", back_populates="terms")


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


class DocRequirement(Base):
    """서류 하나가 갖춰야 하는 요건 중, 약관 조항에 실제로 적혀 있는 것만 담는다.

    예: 제7조 ②항 "사고증명서는 …국외의 의료관련법에서 정한 의료기관에서 발급한 것이어야
    합니다" → 진료비계산서·입원치료확인서 등에 '의료기관 발급' 요건이 붙는다.

    anchor_phrase는 반드시 clause.text의 부분 문자열이어야 한다(ClauseTerm.raw_text와 같은
    규칙). 시드에서 대조 검증하고, 어긋나면 넣지 않는다 — 화면에서 이 문구를 "약관이 요구하는
    것"이라고 인용하기 때문에, 원문에 없는 말이 인용되면 근거 없는 단정이 된다.

    금액·진료일자처럼 약관에 없는 실무 점검 항목은 여기 넣지 않는다. 그건 근거가 없으므로
    services/doc_verify.py의 상수로 따로 두고 화면에서도 칸을 나눠 보여준다.
    """

    __tablename__ = "doc_requirement"

    requirement_id = Column(Integer, primary_key=True)
    required_doc_std_id = Column(Integer, ForeignKey("required_doc_std.required_doc_std_id"), nullable=False)
    code = Column(String, nullable=False)        # ISSUER_MEDICAL 등
    label = Column(String, nullable=False)       # 화면에 쓰는 짧은 말
    anchor_phrase = Column(Text, nullable=False)  # 반드시 clause.text의 부분 문자열
    clause_id = Column(Integer, ForeignKey("clause.clause_id"), nullable=False)

    required_doc_std = relationship("RequiredDocStd")
    clause = relationship("Clause")


class InsurerPremium(Base):
    """보험다모아에서 수집한 나이·성별별 예시 보험료.

    약관에서 뽑아낸 보장 조건과 달리 이 값은 외부 비교공시 사이트에서 가져온 숫자다.
    그래서 어떤 전제(basis)로 산출된 값인지, 어디서 언제 가져왔는지를 행마다 같이
    저장한다 — 근거 없이 숫자만 보여주지 않는다는 원칙은 보험료에도 똑같이 적용한다.
    """
    __tablename__ = "insurer_premium"
    __table_args__ = (UniqueConstraint("insurer_id", "sex", "age", name="uq_premium_insurer_sex_age"),)

    premium_id = Column(Integer, primary_key=True)
    insurer_id = Column(Integer, ForeignKey("insurer.insurer_id"), nullable=False)
    sex = Column(String, nullable=False)          # M/F
    age = Column(Integer, nullable=False)         # 보험나이(만)
    premium = Column(Integer, nullable=False)     # 보험다모아 7일 표준조건 비교공시 보험료(원)
    period_days = Column(Integer, nullable=False, default=7)  # 공시값의 기준 보험기간
    product_name = Column(String)                 # 비교공시상 상품명
    source_product_code = Column(String)          # 보험다모아 상품코드
    age_range = Column(String)                    # 해당 상품의 가입연령 표기(예: "19~79")
    basis = Column(String)                        # 보험료 산출 전제
    source = Column(String)
    source_url = Column(String)
    collected_at = Column(Date)

    insurer = relationship("Insurer")
