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


class TravelAlert(Base):
    """외교부 국가·지역별 여행경보.

    약관에서 뽑은 값이 아니라 외부 기관 자료다(InsurerPremium과 같은 성격). 그래서 행마다
    출처·수집일을 함께 저장하고, 보험사 순위 점수에는 넣지 않는다 — 근거의 출처가 다른
    값을 같은 저울에 올리지 않는다.

    경보 단계 자체는 보상 여부의 근거가 아니다. 단계가 높을 때 "그 보험사 약관에 전쟁·내란
    면책 조항이 있다"는 사실을 조항 원문과 함께 알리는 데까지만 쓴다.
    """

    __tablename__ = "travel_alert"

    alert_id = Column(Integer, primary_key=True)
    country_name = Column(String, nullable=False, index=True)  # 한글 국가명(앱의 국가 목록과 맞춤)
    country_en = Column(String)
    iso_code = Column(String)                 # ISO 2자리
    level = Column(Integer, nullable=False)   # 1 여행유의 / 2 여행자제 / 3 출국권고 / 4 여행금지
    region_type = Column(String)              # 전 지역 / 일부 지역
    note = Column(Text)                       # 경보 내용(일부 지역만 해당하는 경우 등)
    issued_on = Column(String)                # 외교부 작성일
    source = Column(String)
    source_url = Column(String)
    collected_at = Column(Date)


class StandardClause(Base):
    """금융감독원 표준약관(보험업감독업무시행세칙 [별표15])의 조항 원문.

    6개사 Clause와 마찬가지로 원문을 한 글자도 바꾸지 않는다. 이 테이블의 text 자체가
    "근거"이므로 별도 grounding 검증은 필요 없다(ClauseStandardMap의 anchor_phrase가
    이 text의 부분 문자열인지만 검증하면 된다).
    """

    __tablename__ = "standard_clause"
    __table_args__ = (UniqueConstraint("standard_name", "article_no", name="uq_standard_clause_article"),)

    standard_clause_id = Column(Integer, primary_key=True)
    standard_name = Column(String, nullable=False)  # "해외여행 실손의료보험"
    article_no = Column(String, nullable=False)      # "제4조"
    title = Column(String, nullable=False)            # "보상하지 않는 사항"
    text = Column(Text, nullable=False)
    amended_at = Column(String, nullable=True)        # "2026-05-06"
    source_url = Column(String, nullable=False)
    downloaded_at = Column(Date, nullable=True)
    sha256 = Column(String, nullable=True)

    insurer_maps = relationship("ClauseStandardMap", back_populates="standard_clause")


class ClauseStandardMap(Base):
    """보험사 조항 ↔ 표준약관 조항 대응. overlap_rule과 같은 원칙 — 판정을 코드가 아니라
    행 데이터로 두고, 앵커 문구가 원문에 없으면 시드가 예외를 던지고 롤백한다.

    relation:
      SAME                — 표준과 실질적으로 같은 내용
      BROADER             — 이 회사가 표준보다 넓게 보상
      NARROWER             — 이 회사가 표준보다 좁게 보상(표준에 없는 면책·조건 추가 등)
      MISSING_IN_INSURER   — 표준엔 있는데 이 회사 약관에 대응 조항이 없음
                             (이 경우 clause_id/anchor_phrase_insurer는 반드시 NULL)
    """

    __tablename__ = "clause_standard_map"

    map_id = Column(Integer, primary_key=True)
    standard_clause_id = Column(Integer, ForeignKey("standard_clause.standard_clause_id"), nullable=False)
    insurer_id = Column(Integer, ForeignKey("insurer.insurer_id"), nullable=False)
    clause_id = Column(Integer, ForeignKey("clause.clause_id"), nullable=True)
    relation = Column(String, nullable=False)
    anchor_phrase_standard = Column(Text, nullable=False)   # standard_clause.text의 부분 문자열
    anchor_phrase_insurer = Column(Text, nullable=True)     # clause.text의 부분 문자열(clause_id 있을 때만)
    note = Column(Text, nullable=True)

    standard_clause = relationship("StandardClause", back_populates="insurer_maps")
    insurer = relationship("Insurer")
    clause = relationship("Clause")


class FlightDelayStat(Base):
    """한국공항공사 항공기 출도착 지연 통계(보험사 상품설계용으로 공개된 자료).

    약관의 지연기준시간(ClauseTerm term_type='지연기준시간')을 체감 가능한 크기와 나란히
    보여주는 데 쓴다. TravelAlert·InsurerPremium과 같은 성격 — 약관에서 뽑은 값이 아니라
    외부 기관 자료이므로 출처·수집일을 행마다 저장하고 보상 판정 근거나 순위 점수로 쓰지
    않는다.

    원본에 총 운항편수가 없어 "지연 발생 확률(%)"은 계산할 수 없다 — delayed_flights·
    avg_delay_minutes 등 규모만 제공한다(데이터셋 자체의 한계, scope_note 참고).
    """

    __tablename__ = "flight_delay_stat"
    __table_args__ = (UniqueConstraint("year", "kind", "direction", name="uq_flight_delay_year_kind_direction"),)

    stat_id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=True)  # NULL이면 전체기간 합산(overall) 행
    kind = Column(String, nullable=False)       # 국내/국제
    direction = Column(String, nullable=False)  # 출발/도착
    delayed_flights = Column(Integer, nullable=False)
    total_delay_minutes = Column(Integer, nullable=False)
    avg_delay_minutes = Column(Float, nullable=True)
    passengers_affected = Column(Integer, nullable=True)
    source = Column(String)
    source_url = Column(String)
    scope_note = Column(Text)
    collected_at = Column(Date)


class NonpaymentRate(Base):
    """손해보험협회 공시실(consumer.knia.or.kr) — 보험금 부지급률/청구이후 해지비율.

    TravelAlert·InsurerPremium과 같은 성격의 외부 공시 자료다. **전체 보험종목** 기준
    공시라 여행자보험만의 부지급률이 아니다 — "이 보험사가 전반적으로 보험금을 얼마나
    안 주는 편인가"를 보여주는 참고 지표로만 쓴다. 약관 근거가 아니므로 순위 점수에
    넣지 않는다(InsurerPremium과 동일 원칙).

    insurer_id가 NULL이면 업계평균(company_name='업계평균') 행이거나, 우리 6개사 밖의
    손보사 행이다 — 조용히 버리지 않고 원본 그대로 저장해 두되(company_name), 화면에는
    6개사 + 업계평균만 노출한다.
    """

    __tablename__ = "nonpayment_rate"
    __table_args__ = (UniqueConstraint("period", "company_name", name="uq_nonpayment_period_company"),)

    rate_id = Column(Integer, primary_key=True)
    insurer_id = Column(Integer, ForeignKey("insurer.insurer_id"), nullable=True)
    company_name = Column(String, nullable=False)  # 공시 원문 회사명(업계평균 포함)
    period = Column(String, nullable=False)          # "2025년 하반기"
    claim_count = Column(Integer, nullable=False)
    paid_count = Column(Integer, nullable=False)
    unpaid_count = Column(Integer, nullable=False)
    unpaid_rate = Column(Float, nullable=False)             # 부지급률(%) = 부지급건수/청구건수*100
    claim_contract_count = Column(Integer, nullable=True)
    post_claim_cancel_count = Column(Integer, nullable=True)
    post_claim_cancel_rate = Column(Float, nullable=True)   # 청구이후 해지비율(%)
    source = Column(String)
    source_url = Column(String)
    scope_note = Column(Text)
    collected_at = Column(Date)

    insurer = relationship("Insurer")


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
    premium = Column(Integer, nullable=False)     # 보험다모아 표준조건 비교공시 보험료(원)
    period_days = Column(Integer, nullable=False, default=7)  # 공시값의 기준 보험기간
    product_name = Column(String)                 # 비교공시상 상품명
    source_product_code = Column(String)          # 보험다모아 상품코드
    age_range = Column(String)                    # 해당 상품의 가입연령 표기(예: "19~79")
    basis = Column(String)                        # 보험료 산출 전제
    source = Column(String)
    source_url = Column(String)
    collected_at = Column(Date)

    insurer = relationship("Insurer")


class CountryLanguage(Base):
    """한국어 국가명 → 그 나라 서류 창구에서 통하는 언어.

    country_name 표기는 TravelAlert.country_name과 맞춘다(둘 다 외교부 국가명 기준).
    매핑이 없는 나라는 추측하지 않고 영어로 떨어뜨린다 — 화면에는 한국어가 항상 병기되므로
    언어를 잘못 골라도 정보가 사라지지는 않는다.
    """

    __tablename__ = "country_language"
    __table_args__ = (UniqueConstraint("country_name", "lang_code", name="uq_country_language"),)

    id = Column(Integer, primary_key=True)
    country_name = Column(String, nullable=False, index=True)
    lang_code = Column(String, nullable=False)     # ISO 639-1
    lang_name_ko = Column(String, nullable=False)  # "영어"
    is_primary = Column(Boolean, default=True)


class OnsitePhraseI18n(Base):
    """현지어 문구 캐시.

    **조항 원문은 여기 들어오지 않는다.** 조항은 근거 그 자체라 번역하지 않고 한국어 원문
    그대로 인용한다. 여기 담기는 것은 서류명(RequiredDocStd.doc_name), 요건 표시문구
    (DocRequirement.label), 창구에 보여줄 안내문 세 가지뿐이다.

    source='seed'는 사람이 검수해 커밋한 번역, 'gemini'는 런타임에 만들어 캐시한 번역이다.
    같은 (kind, ref_id, lang_code)를 두 번 만들지 않으므로 두 번째 사용자부터는 API 호출이
    없고, 오프라인 캐시에도 그대로 실린다.
    """

    __tablename__ = "onsite_phrase_i18n"
    __table_args__ = (UniqueConstraint("kind", "ref_id", "lang_code", name="uq_onsite_phrase"),)

    KIND_DOC_NAME = "doc_name"
    KIND_REQUIREMENT = "requirement"
    KIND_INTRO = "intro"
    ALLOWED_KINDS = (KIND_DOC_NAME, KIND_REQUIREMENT, KIND_INTRO)

    id = Column(Integer, primary_key=True)
    kind = Column(String, nullable=False)
    ref_id = Column(Integer, nullable=False)   # required_doc_std_id | requirement_id | 0(intro)
    lang_code = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    source = Column(String, nullable=False)    # seed | gemini


class SimulationScenario(Base):
    """여행 정보로 자동 선정되는 사고 시나리오(L1 단위).

    선정 조건을 코드 분기가 아니라 행으로 두는 이유는 OverlapRule과 같다 — 시나리오가
    늘어나도 선정 로직은 늘어나지 않는다.

    type_id는 반드시 L1 루트 행(IncidentType.parent_id IS NULL)을 가리킨다. L2 세분화는
    사용자가 화면에서 고르고 요청 파라미터로만 전달된다 — 시뮬레이션에는 자유서술이 없어
    L2를 추론할 근거가 없으므로, 추측하지 않고 사람이 고르게 한다.
    """

    __tablename__ = "simulation_scenario"

    scenario_id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    narrative = Column(Text, nullable=False)
    type_id = Column(Integer, ForeignKey("incident_type.type_id"), nullable=False)
    modifiers = Column(Text)                       # JSON, 예: {"activity": "스쿠버다이빙"}
    # 선정 조건 — 전부 비어 있으면 항상 뜨는 기본 시나리오
    require_activity = Column(String)
    require_rental_car = Column(Boolean)
    require_alert_nationwide = Column(Boolean)
    sort_order = Column(Integer, default=0)

    incident_type = relationship("IncidentType")
