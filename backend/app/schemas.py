import datetime as dt
from typing import Optional

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


class InsurerPremiumOut(BaseModel):
    """나이·성별 하나에 대한 보험사별 예시 보험료 한 줄."""
    insurer_code: str
    insurer_name: str
    product_name: Optional[str] = None
    premium: int              # 비교공시 기준 보험료(1건)
    premium_total: int        # 여행일수를 곱한 총액
    age_range: Optional[str] = None


class PremiumPointOut(BaseModel):
    age: int
    premium: int


class InsurerPremiumCurveOut(BaseModel):
    """한 보험사의 나이별 보험료 곡선."""
    insurer_code: str
    insurer_name: str
    product_name: Optional[str] = None
    sex: str
    points: list[PremiumPointOut]


class PremiumComparisonOut(BaseModel):
    """보험료는 외부 비교공시에서 가져온 값이라 전제·출처를 항상 함께 내려보낸다."""
    age: int
    sex: str
    basis: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    collected_at: Optional[dt.date] = None
    days: int = 1
    items: list[InsurerPremiumOut]
    unavailable_insurers: list[str] = []


class UserPolicyOut(BaseModel):
    user_policy_id: int
    insurer_name_raw: str
    product_name_raw: Optional[str]
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
    # 게스트(비로그인)는 "내 보험"을 쓸 수 없어 등록된 보험이 없다 — 대신 6개 보험사 중
    # 하나를 바로 고르면, 서버가 그 보험사로 최소한의 보험 기록을 대신 만들어 청구 검토에 쓴다.
    insurer_code: Optional[str] = None
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


class InsurerRankOut(BaseModel):
    rank: int
    insurer_code: str
    insurer_name: str
    comparison_basis: str
    dimensions: list[RankingDimensionOut]
    reasons: list[str]
    tags: list[str] = []
    official_url: Optional[str] = None
    # 나이·성별을 함께 받은 경우에만 채워진다(보험다모아 비교공시 기준 예시 보험료).
    premium: Optional[int] = None            # 비교공시에서 받아온 기준 보험료(1건)
    premium_total: Optional[int] = None      # 여행일수를 곱한 총액 — 화면에는 이 값을 보여준다
    premium_days: Optional[int] = None       # 총액 계산에 쓴 여행일수
    premium_note: Optional[str] = None


class InsurerRankingOut(BaseModel):
    tier_code: str
    ranking: list[InsurerRankOut]


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
