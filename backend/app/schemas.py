import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class TripCreate(BaseModel):
    user_id: int
    destination: str
    start_date: dt.date
    end_date: dt.date
    purpose: str
    activities: list[str] = []
    companion_type: Optional[str] = None
    rental_car: bool = False
    coverage_priority: list[str] = []
    # 목적지에 3·4단계 지역경보가 있을 때, 사용자가 "그 지역에 간다"고 체크한 항목의
    # travel_alert.alert_id. 체크하지 않으면 빈 목록이고 아무 일도 일어나지 않는다 —
    # 일본의 3단계는 후쿠시마 원전 30km라, 도쿄 여행자에게 면책 조항을 들이밀지 않는다.
    visiting_alert_region_ids: list[int] = []


class TripUpdate(BaseModel):
    """이미 등록한 여행의 기본 정보 수정 — 사고 접수 중에 급히 만든 여행을 나중에
    제대로 채워 넣을 수 있게 한다. 넘긴 항목만 바뀐다."""
    destination: Optional[str] = None
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    purpose: Optional[str] = None
    companion_type: Optional[str] = None


class TripDetailOut(BaseModel):
    trip_id: int
    destination: Optional[str] = None
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    purpose: Optional[str] = None
    companion_type: Optional[str] = None
    user_policy_id: Optional[int] = None
    insurer_name: Optional[str] = None


class HighlightSpanOut(BaseModel):
    text: str
    color: str


class ClauseTermOut(BaseModel):
    term_type: str  # 지급한도/자기부담금/면책일수/지연기준시간 ...
    value_num: Optional[float] = None
    unit: Optional[str] = None  # 원/일/시간/%
    basis: Optional[str] = None  # 실손/정액 ...
    condition_text: Optional[str] = None
    raw_text: str  # 조항 원문 중 이 수치의 근거가 된 부분(그대로 인용)

    class Config:
        from_attributes = True


class ClauseOut(BaseModel):
    clause_id: int
    article_no: str
    text: str
    page_ref: Optional[str]
    default_color: str
    highlight_color: str
    highlight_spans: Optional[list[HighlightSpanOut]] = None
    terms: list[ClauseTermOut] = []

    # 일부 조항(seed 스크립트 누락)은 default_color가 DB에 NULL로 남아있을 수 있다.
    # 색상 하나 누락됐다고 전체 API 응답이 500으로 죽으면 안 되므로, 여기서 무채색(회색)으로
    # 안전하게 대체한다 — 근거 조항 자체는 그대로 보여주는 게 우선이다.
    @field_validator("default_color", "highlight_color", mode="before")
    @classmethod
    def _fallback_color(cls, v):
        return v or "회색"

    class Config:
        from_attributes = True


class FindingOut(BaseModel):
    finding_id: int
    finding_type: str
    status: str
    target_ref: Optional[str]
    insurer_code: Optional[str] = None
    insurer_name: Optional[str] = None
    description: str
    confidence: Optional[str]
    coverage_amount: Optional[str] = None
    #: 등록한 등급 기준 실제 가입금액("5,000만원 (실속형 기준)"). 약관 한도와 다른 값이라
    #: 같은 칸에 섞지 않고 따로 둔다.
    plan_amount: Optional[str] = None
    clauses: list[ClauseOut]


class RecommendationOut(BaseModel):
    analysis_run_id: int
    trip_id: int
    risk_profile: dict
    findings: list[FindingOut]


class UserCoverageIn(BaseModel):
    raw_name: str
    subscribed_amount: Optional[str] = None
    coverage_id: Optional[int] = None  # 실제 KB 담보 체크리스트에서 선택한 경우, 그 담보를 그대로 지정(퍼지 매칭 생략)


class UserPolicyCreate(BaseModel):
    # 이 보험이 어느 여행에 대한 것인지. 넘기면 그 여행에 보험이 연결돼서, 나중에 사고를
    # 접수할 때 "어느 여행의 어느 보험으로 청구하는지"가 자동으로 이어진다.
    trip_id: Optional[int] = None
    insurer_name_raw: str
    product_name_raw: Optional[str] = None
    # 그 보험사가 실제로 파는 등급명(예: "표준형"). 몰라도 등록할 수 있게 선택값이다.
    plan_name: Optional[str] = None
    subscriber_age: Optional[int] = None
    period_start: dt.date
    period_end: dt.date
    # 담보는 더 이상 프론트에서 직접 고르지 않는다 — 매칭된 상품의 실제 담보 목록을
    # 서버가 자동으로 채운다(insurers.py의 실제 Coverage 데이터 기준). 과거 호환용으로만 남김.
    coverages: list[UserCoverageIn] = []


class UserCoverageOut(BaseModel):
    user_coverage_id: int
    raw_name: str
    subscribed_amount: Optional[str]
    matched_std_code: Optional[str] = None
    matched_std_name: Optional[str] = None
    match_confidence: float


class InsurerCoverageOut(BaseModel):
    coverage_id: int
    std_code: Optional[str] = None
    std_name: Optional[str] = None
    raw_name: str
    definition: Optional[str] = None
    limit_amount: Optional[str] = None
    deductible: Optional[str] = None


PremiumValueOrigin = Literal["DIRECT_QUOTE", "DERIVED", "IMPUTED", "UNKNOWN"]


class PremiumProvenanceOut(BaseModel):
    value_origin: PremiumValueOrigin = "UNKNOWN"
    source_value: Optional[int] = None
    source_period_days: Optional[int] = None
    transformation: Optional[str] = None
    transformation_reason: Optional[str] = None
    source_reference: Optional[str] = None


class InsurerPremiumOut(PremiumProvenanceOut):
    """나이·성별 하나에 대한 보험사별 보험료와 값의 생성 경로."""
    insurer_code: str
    insurer_name: str
    product_name: Optional[str] = None  # 대표로 보여주는 등급명(예: "표준형")
    published_premium: int
    premium_period_days: int
    age_range: Optional[str] = None
    #: 이 보험사의 산출 전제와 조회일. 보험사마다 다르다 — 예를 들어 삼성은 항공지연 지수형
    #: 특약 2종이 기본 포함된 값이고, 조회일도 2026-08-17(최초 6개사)·08-23(DB)·08-25(신한)로
    #: 갈린다. 바깥의 basis/collected_at 하나로 뭉뚱그리면 다른 전제로 조회한 값을 같은
    #: 조건으로 비교한 것처럼 보여주게 된다.
    basis: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    collected_at: Optional[dt.date] = None


class PremiumPointOut(PremiumProvenanceOut):
    age: int
    published_premium: int
    premium_period_days: int


class InsurerPremiumCurveOut(BaseModel):
    """한 보험사의 나이별 보험료 곡선(표준 등급 하나 대표)."""
    insurer_code: str
    insurer_name: str
    product_name: Optional[str] = None
    sex: str
    premium_period_days: int = 7
    basis: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    collected_at: Optional[dt.date] = None
    points: list[PremiumPointOut]


class PremiumComparisonOut(BaseModel):
    """보험료와 직접조회/환산/추정 provenance를 함께 내려보낸다."""
    age: int
    sex: str
    #: 보험사마다 다를 수 있는 값의 대표치다. 정확한 전제·조회일은 items 각각에 붙어 있다.
    basis: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    #: 표시된 보험사들 중 **가장 최근** 조회일. 예전에는 목록 첫 줄(=제일 싼 보험사)의 값을
    #: 그대로 썼는데, 그러면 나중에 조회한 보험사가 섞여 있어도 화면에는 옛 날짜가 뜬다.
    collected_at: Optional[dt.date] = None
    premium_period_days: int = 7
    items: list[InsurerPremiumOut]
    unavailable_insurers: list[str] = []  # 가격을 추적 중인데 이 나이만 가입연령 범위 밖인 보험사(이름)
    no_data_insurer_codes: list[str] = []  # 나이와 무관하게 가격을 아직 하나도 못 구한 보험사(코드)


# --- 보험사 등급(플랜) — 가격·담보한도 비교 --------------------------------

class InsurerPlanOut(PremiumProvenanceOut):
    """보험사 한 곳의 등급 하나와 보험료 provenance."""
    plan_name: str
    premium: int
    premium_period_days: int = 1
    is_standard_tier: bool
    collected_at: Optional[dt.date] = None


class InsurerPlansOut(BaseModel):
    insurer_code: str
    insurer_name: str
    premium_period_days: int = 1
    plans: list[InsurerPlanOut]
    #: 이 나이·성별 자료 자체가 없으면 True — 등급 칩은 이름만, 가격 없이 보여준다.
    price_unavailable: bool = False


class InsurerPlanCoverageRowOut(BaseModel):
    plan_name: str
    coverage_label: str
    #: 원문 표기 그대로("10000", "-", "미가입(손해액기준)" 등) — 숫자로 강제 변환하지 않는다.
    amount_text: str
    unit: str
    sort_order: int


class InsurerPlanCoverageOut(BaseModel):
    """보험사 다이렉트 사이트에서 직접 조회한 등급별 담보 가입금액표.

    약관 조항에서 뽑은 값이 아니라 외부(보험사 공시 화면)에서 가져온 값이므로
    UserCoverage(실제 약관 Coverage 기준)와는 다른 목적이다 — 이건 가입 전
    "어느 등급을 고를지" 비교하는 용도고, UserCoverage는 실제로 등록한 보험의
    청구 검토 근거다. 둘을 섞지 않는다."""
    insurer_code: str
    insurer_name: str
    plan_names: list[str]  # 원문 등급 순서 그대로(중복 없이)
    rows: list[InsurerPlanCoverageRowOut]
    source: Optional[str] = None
    source_note: Optional[str] = None
    collected_at: Optional[dt.date] = None


class ComparisonMetricValueOut(BaseModel):
    insurer_code: str
    value_text: str


class ComparisonMetricOut(BaseModel):
    metric_label: str
    unit: str
    values: list[ComparisonMetricValueOut]


class ComparisonCategoryOut(BaseModel):
    category: str
    metrics: list[ComparisonMetricOut]


class InsurerComparisonOut(BaseModel):
    """전 보험사를 같은 담보 항목 기준으로 나란히 비교한 표(보장비교 종합), 등급 하나 기준.

    InsurerPlanCoverageOut과 다른 점: 그건 보험사 하나의 원문 담보명 그대로를 보여주고,
    이건 사람이 재정리한 공통 항목(metric_label)으로 나란히 비교한다."""
    tier_rank: int
    tier_label: str
    categories: list[ComparisonCategoryOut]
    source: Optional[str] = None
    source_note: Optional[str] = None
    collected_at: Optional[dt.date] = None


class UserPolicyOut(BaseModel):
    user_policy_id: int
    insurer_name_raw: str
    product_name_raw: Optional[str]
    plan_name: Optional[str] = None
    subscriber_age: Optional[int] = None
    period_start: dt.date
    period_end: dt.date
    matched_insurer_code: Optional[str] = None
    matched_insurer_name: Optional[str] = None
    matched_product_name: Optional[str] = None
    coverages: list[UserCoverageOut]


class IncidentCreate(BaseModel):
    user_id: int
    trip_id: Optional[int] = None
    # 연결할 여행이 아직 없을 때, 사고 접수 화면에서 목적지·기간만 받아 여행도 같이 만든다.
    # (trip_id가 오면 이 값들은 무시한다.)
    new_trip_destination: Optional[str] = None
    new_trip_start_date: Optional[dt.date] = None
    new_trip_end_date: Optional[dt.date] = None
    user_policy_id: Optional[int] = None  # 이 사고 청구가 어느 등록 보험을 대상으로 하는지
    # 게스트(비로그인)는 "내 보험"을 쓸 수 없어 등록된 보험이 없다 — 대신 비교 대상 보험사 중
    # 하나를 바로 고르면, 서버가 그 보험사로 최소한의 보험 기록을 대신 만들어 청구 검토에 쓴다.
    insurer_code: Optional[str] = None
    # insurer_code와 함께 등급도 골랐으면 같이 남긴다(선택값 — 몰라도 접수할 수 있다).
    plan_name: Optional[str] = None
    free_text: str = ""
    country: Optional[str] = None
    occurred_at: Optional[dt.datetime] = None
    cause: Optional[str] = None
    injury_part: Optional[str] = None
    diagnosis: Optional[str] = None
    hospitalized: Optional[bool] = None
    surgery: Optional[bool] = None
    local_treatment: Optional[bool] = None
    medical_cost: Optional[str] = None
    returned_home: Optional[bool] = None


class PendingQuestionOut(BaseModel):
    question_id: int
    question_text: str
    target_field: str
    impact_weight: float
    #: "yesno"면 예/아니오 버튼, "text"면 한 줄 입력칸으로 그린다.
    answer_type: str = "text"
    #: "L1"(대분류 확인) | "L2"(세부유형 확인). 옛 공용 질문은 None이다.
    stage: Optional[str] = None


class ValidationResultOut(BaseModel):
    rule_code: str
    rule_name: str
    severity: str
    passed: bool
    detail: str


class IncidentAnalysisOut(BaseModel):
    incident_id: int
    analysis_run_id: int
    structured: dict
    findings: list[FindingOut]
    pending_questions: list[PendingQuestionOut]
    validation_results: list[ValidationResultOut] = []
    linked_insurer_code: Optional[str] = None
    linked_insurer_name: Optional[str] = None
    linked_product_name: Optional[str] = None
    # 이 사고가 어느 여행과 연결됐는지 — 서류체크/실수방지/약관형광펜 화면에서 "무슨 여행 중
    # 사고인지"를 한눈에 보여주기 위함. 연결된 여행(trip)이 없으면 사고 접수 시 직접 입력한
    # country만 대신 보여준다(둘 다 없으면 전부 None).
    trip_id: Optional[int] = None
    trip_destination: Optional[str] = None
    trip_start_date: Optional[str] = None
    trip_end_date: Optional[str] = None
    incident_country: Optional[str] = None


class AnswerIn(BaseModel):
    question_id: int
    answer_text: str


class AnswerBatchIn(BaseModel):
    """한 페이지에 뜬 질문의 답을 한 번에 받는다.

    답마다 따로 저장하면 같은 사고 분석이 답변 수만큼 돌아서, 응답이 그만큼 느려지고
    중간 상태가 섞인 결과가 나온다."""
    answers: list[AnswerIn] = []
    #: 예/아니오로 다 담기지 않는 이야기를 받는 칸. 사고 수식자로 남아 재분류에 쓰인다.
    extra_note: Optional[str] = None


class ChecklistItemOut(BaseModel):
    required_doc_std_id: int
    doc_code: str
    doc_name: str
    acquire_location: str
    is_mandatory: bool
    coverage_target_ref: str
    insurer_name: str
    status: str  # 보유/미보유/발급불가/미확인
    memo: Optional[str] = None
    clause: Optional[ClauseOut] = None


class EvidenceIn(BaseModel):
    required_doc_std_id: int
    status: str  # 보유/미보유/발급불가
    memo: Optional[str] = None


class ChecklistOut(BaseModel):
    incident_id: int
    items: list[ChecklistItemOut]
    validation_results: list[ValidationResultOut] = []
    trip_id: Optional[int] = None
    trip_destination: Optional[str] = None
    trip_start_date: Optional[str] = None
    trip_end_date: Optional[str] = None
    incident_country: Optional[str] = None


class DocCheckOut(BaseModel):
    """서류 요건 하나의 확인 결과.

    clause_* 가 채워진 항목만 '약관이 요구하는 것'이다. 비어 있으면 약관 근거가 없는
    실무 점검 항목이며, 화면에서도 칸을 나눠 그렇게 밝힌다."""
    code: str
    label: str
    found: bool
    quote: Optional[str] = None          # 서류에서 근거가 된 문구
    clause_article_no: Optional[str] = None
    clause_text: Optional[str] = None    # 조항 원문 중 근거가 된 부분


class DocVerifyOut(BaseModel):
    """사진 확인 결과. 이 응답에만 번역문이 담기고 서버에는 남지 않는다."""
    required_doc_std_id: int
    doc_name: str
    readable: bool
    detected_doc_type: Optional[str] = None
    language: Optional[str] = None
    translation: Optional[str] = None
    message: str
    applied_status: Optional[str] = None  # 체크리스트에 실제로 반영한 상태(없으면 그대로 둠)
    grounded: list[DocCheckOut] = []
    practical: list[DocCheckOut] = []
    checklist: ChecklistOut


class IncidentTypeOut(BaseModel):
    type_id: int
    l1_code: str
    name: str


class StandardClauseOut(BaseModel):
    standard_clause_id: int
    article_no: str
    title: str
    text: str
    amended_at: Optional[str] = None

    class Config:
        from_attributes = True


class StandardClauseComparisonOut(BaseModel):
    """표준약관 조문 하나에 대한 특정 보험사의 대조 결과 한 칸.

    relation이 MISSING_IN_INSURER면 insurer_clause*는 전부 None이다 — 대응 조항이
    없다는 사실 자체가 결과이므로, 억지로 다른 조항을 끌어와 채우지 않는다."""
    standard_clause_id: int
    article_no: str
    title: str
    standard_text: str
    anchor_phrase_standard: str
    relation: str  # SAME/BROADER/NARROWER/MISSING_IN_INSURER
    insurer_clause_id: Optional[int] = None
    insurer_article_no: Optional[str] = None
    insurer_text: Optional[str] = None
    anchor_phrase_insurer: Optional[str] = None
    note: Optional[str] = None


class InsurerStandardComparisonOut(BaseModel):
    insurer_code: str
    insurer_name: str
    standard_name: str
    source_url: str
    amended_at: Optional[str] = None
    items: list[StandardClauseComparisonOut] = []


class FlightDelayStatOut(BaseModel):
    kind: str        # 국내/국제
    direction: str    # 출발/도착
    delayed_flights: int
    avg_delay_minutes: Optional[float] = None
    passengers_affected: Optional[int] = None

    class Config:
        from_attributes = True


class FlightDelayStatsOut(BaseModel):
    """약관의 지연기준시간을 체감 가능한 크기와 나란히 보여주기 위한 참고 통계.

    총 운항편수가 원본에 없어 '지연 발생 확률(%)'은 계산할 수 없다 — 규모(건수·평균
    지연시간)만 제공한다. 보상 판정 근거나 순위 점수로 쓰지 않는다."""
    source: str
    source_url: str
    coverage_period: str
    scope_note: str
    collected_at: Optional[dt.date] = None
    overall: list[FlightDelayStatOut]


class ClauseIncidentLinkOut(BaseModel):
    type_name: str
    relevance: str  # 직접/조건부/면책


class ClauseSearchResultOut(BaseModel):
    clause: ClauseOut
    incident_links: list[ClauseIncidentLinkOut] = []


class NonpaymentRateOut(BaseModel):
    insurer_code: Optional[str] = None
    company_name: str
    claim_count: int
    unpaid_count: int
    unpaid_rate: float
    post_claim_cancel_rate: Optional[float] = None

    class Config:
        from_attributes = True


class NonpaymentRatesOut(BaseModel):
    """손해보험협회 공시(부지급률 등). 전체 보험종목 기준이라 여행자보험 단독 수치가
    아니다 — 참고 지표로만 쓰고 보험사 순위 점수에는 넣지 않는다."""
    source: str
    source_url: str
    period: str
    scope_note: str
    collected_at: Optional[dt.date] = None
    items: list[NonpaymentRateOut]
    industry_average: Optional[NonpaymentRateOut] = None


class InsurerIncidentCoverageOut(BaseModel):
    """가입 전, 특정 보험사가 특정 사고유형(L1)을 실제로 어떤 담보·조항으로 보상하는지.
    사용자가 등록한 보험이 없어도(아직 가입 전이므로) 그 보험사의 KB(약관 원문) 자체를
    기준으로 조회한다는 점이 사고 후 청구검토(claim_review.py)와 다르다."""
    coverage_id: int
    coverage_name: str
    relevance: str  # 직접/조건부/면책
    limit_amount: Optional[str] = None
    clauses: list[ClauseOut] = []


class InsurerTierOut(BaseModel):
    tier_code: str
    label: str
    description: str


class RankingEvidenceOut(BaseModel):
    kind: str
    source_id: int
    coverage_name: str
    description: str
    page_ref: Optional[str] = None


class RankingDimensionOut(BaseModel):
    code: str
    label: str
    level: int  # 보험사 사이 상대 단계 1~5, 근거 부족은 0
    status: str
    summary: str
    evidence_count: int
    evidence: list[RankingEvidenceOut] = []
    comparison_state: Literal["AVAILABLE", "UNKNOWN", "NOT_APPLICABLE"]
    available: bool
    known_count: int
    total_count: int
    completeness_rate: Optional[float] = None


class RankingAxisOut(BaseModel):
    """이번 순위에서 이 축이 몇 점을 얼마나 기여했는지. "왜 이 순서인지"를 화면에서
    그대로 되짚을 수 있게 점수·비중·기여도를 다 내려보낸다."""
    code: str          # amount | clause | price | overlap | activity
    label: str
    score: float       # 0~1
    weight: float      # 이 계산에 실제로 쓰인 비중(자료 없는 축을 빼고 재정규화한 값)
    contribution: float  # score × weight × 100
    available: bool    # False면 자료가 없어 이 축을 빼고 나머지로 100%를 다시 맞췄다
    detail: str
    comparison_state: Literal["AVAILABLE", "UNKNOWN", "NOT_APPLICABLE"]


class InsurerRankOut(BaseModel):
    rank: int
    insurer_code: str
    insurer_name: str
    comparison_basis: str
    dimensions: list[RankingDimensionOut]
    reasons: list[str]
    tags: list[str] = []
    official_url: Optional[str] = None
    # 나이·성별을 함께 받은 경우에만 채워진다. 여행일수로 새 견적을 만들지 않는다.
    published_premium: Optional[int] = None
    # published_premium이 어느 등급 가격인지(plan_tier로 고른 등급, 또는 기본 표준 등급).
    # 이 보험사 상세 화면(등급 선택)에 처음 들어갈 때 여기 등급을 그대로 이어서 보여준다 —
    # 안 그러면 목록에서 "고급"을 봐 놓고 상세 화면은 "표준"으로 되돌아가 버린다.
    plan_name: Optional[str] = None
    premium_period_days: Optional[int] = None
    premium_basis: Optional[str] = None
    premium_source: Optional[str] = None
    premium_source_url: Optional[str] = None
    premium_collected_at: Optional[dt.date] = None
    premium_value_origin: Optional[PremiumValueOrigin] = None
    premium_source_value: Optional[int] = None
    premium_source_period_days: Optional[int] = None
    premium_transformation: Optional[str] = None
    premium_transformation_reason: Optional[str] = None
    premium_source_reference: Optional[str] = None
    premium_note: Optional[str] = None
    # 가중치 점수 모델의 결과. plan_tier를 함께 받았을 때만 채워진다.
    total_score: Optional[float] = None
    axes: list[RankingAxisOut] = []
    # 등급별 담보 가입금액표(InsurerPlanCoverage)를 볼 수 있는 보험사면 그 담보 항목 수.
    # None이면 아직 자료가 없다는 뜻 — 순위 점수에는 섞이지 않는다(published_premium과 동일 원칙).
    plan_coverage_item_count: Optional[int] = None


class InsurerRankingOut(BaseModel):
    tier_code: str
    ranking: list[InsurerRankOut]
    #: 그 등급 상품이 없어 비교에서 빠진 보험사가 있으면 그 사실을 한 줄로 알린다 —
    #: 아무 말 없이 목록에서 사라지면 사용자는 자료가 누락된 걸로 읽는다.
    excluded_note: Optional[str] = None


class ExternalPolicyLinkItem(BaseModel):
    kind: str
    insurer_name_raw: Optional[str] = None
    product_name_raw: Optional[str] = None
    enrolled_ym: Optional[str] = None


class ExternalPolicyLinkRequest(BaseModel):
    """등록 진입점은 수집 방식과 무관하게 하나다 — 수동입력도 provider='manual'로 들어온다."""
    provider: str = "manual"
    items: list[ExternalPolicyLinkItem] = []


class ExternalCoverageOut(BaseModel):
    external_coverage_id: int
    raw_name: Optional[str] = None
    subscribed_amount: Optional[str] = None
    amount_source: str

    class Config:
        from_attributes = True


class ExternalPolicyOut(BaseModel):
    external_policy_id: int
    source: str
    kind: str
    insurer_name_raw: Optional[str] = None
    product_name_raw: Optional[str] = None
    enrolled_ym: Optional[str] = None
    indemnity_gen: Optional[int] = None
    coverages: list[ExternalCoverageOut] = []

    class Config:
        from_attributes = True


class ProviderOut(BaseModel):
    name: str
    requires_login: bool


class OverlapFindingOut(BaseModel):
    coverage_std_code: str
    coverage_std_name: str
    external_kind: str
    scope: str
    relation: str
    note: Optional[str] = None
    clause_id: Optional[int] = None
    clause_article_no: Optional[str] = None
    clause_quote: Optional[str] = None


class OverlapReportOut(BaseModel):
    duplicates: list[OverlapFindingOut] = []
    gaps: list[OverlapFindingOut] = []
    fixed_ok: list[OverlapFindingOut] = []
    unknown: list[OverlapFindingOut] = []


# --- 현지 대응 팩(「현지에서」) --------------------------------------------
# 한 번의 요청으로 사고유형 8개분을 전부 담는다. 오프라인 캐시에 실리는 단위가 요청
# 하나여야 비행기모드에서 화면이 온전히 뜬다(services/onsite.py 참고).

class OnsiteRequirementOut(BaseModel):
    #: 한국어 원문. 현지어만 단독으로 나가는 일이 없도록 항상 채운다.
    label_ko: str
    #: 번역을 못 구하면 None — 빈 문자열이나 한국어를 대신 넣지 않는다(번역된 척하지 않는다).
    label_local: Optional[str] = None
    clause_id: Optional[int] = None
    clause_article_no: Optional[str] = None
    #: 조항 원문의 부분 문자열. 근거는 번역하지 않는다.
    clause_quote: Optional[str] = None
    insurer_name: Optional[str] = None


class OnsiteDocOut(BaseModel):
    required_doc_std_id: int
    doc_code: str
    doc_name_ko: str
    doc_name_local: Optional[str] = None
    acquire_location: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None
    requirements: list[OnsiteRequirementOut] = []


class OnsiteIncidentTypeOut(BaseModel):
    type_id: int
    l1_code: str
    name: str


class OnsitePackOut(BaseModel):
    country: Optional[str] = None
    lang_code: str
    lang_name_ko: str
    intro_ko: str
    intro_local: Optional[str] = None
    trip_id: Optional[int] = None
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    insurer_names: list[str] = []
    incident_types: list[OnsiteIncidentTypeOut] = []
    docs_by_type: dict[int, list[OnsiteDocOut]] = {}
    #: 연결된 사고가 있을 때만. 없으면 0/N으로 지어내지 않고 None으로 둔다.
    progress_total: Optional[int] = None
    progress_secured: Optional[int] = None
    generated_at: dt.datetime


# --- 사고 시뮬레이션 --------------------------------------------------------

class SimulationResultOut(BaseModel):
    insurer_name: str
    #: 직접 | 조건부 | 면책 | 확인불가
    verdict: str
    coverage_name: Optional[str] = None
    clause_article_no: Optional[str] = None
    clause_quote: Optional[str] = None


class SimulationSubTypeOut(BaseModel):
    type_id: int
    name: str


class SimulatedScenarioOut(BaseModel):
    code: str
    title: str
    narrative: str
    l1_type_id: int
    selected_type_id: int
    incident_type_name: str
    sub_types: list[SimulationSubTypeOut] = []
    results: list[SimulationResultOut] = []


class SimulationOut(BaseModel):
    trip_id: int
    destination: Optional[str] = None
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    scenarios: list[SimulatedScenarioOut] = []
    #: 화면에 고정으로 띄우는 경계 문구. 서버가 내려보내 화면과 테스트가 같은 문장을 쓴다.
    disclaimer: str


# --- 근거 검증 현황 ---------------------------------------------------------
# "근거 없는 결과를 내지 않는다"는 이 프로젝트의 원칙인데, 그게 지켜지고 있다는 사실은
# 지금까지 문서에만 있었다. 아래 스키마는 그 검증을 앱 안에서 DB 실측으로 보여주기 위한 것이다.

class KbCheckOut(BaseModel):
    """"몇 건 중 몇 건이 근거를 갖췄는가"를 담는 한 줄."""
    code: str
    label: str
    #: 이 검사가 무엇을 확인하는지, 왜 그게 근거가 되는지 한 문장.
    description: str
    passed: int
    total: int
    #: 통과율(%). 소수점 첫째 자리까지.
    rate: float


class KbInsurerStatOut(BaseModel):
    insurer_code: str
    insurer_name: str
    clause_count: int
    coverage_count: int
    clause_term_count: int
    incident_map_count: int
    #: 이 보험사에서 읽은 약관 판본. 어느 판을 읽었는지가 근거의 일부다.
    version_label: Optional[str] = None
    effective_date: Optional[dt.date] = None
    #: 원본 PDF의 SHA-256 앞 12자리. 같은 파일을 읽었는지 대조할 수 있게 남긴다.
    file_hash_prefix: Optional[str] = None


class KbStatsOut(BaseModel):
    insurer_count: int
    clause_count: int
    coverage_count: int
    clause_term_count: int
    incident_map_count: int
    incident_type_l1_count: int
    incident_type_l2_count: int
    checks: list[KbCheckOut] = []
    insurers: list[KbInsurerStatOut] = []
