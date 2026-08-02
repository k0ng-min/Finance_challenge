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


class InsurerRankOut(BaseModel):
    rank: int
    insurer_code: str
    insurer_name: str
    score: float
    reasons: list[str]
    tags: list[str] = []
    official_url: Optional[str] = None


class InsurerRankingOut(BaseModel):
    tier_code: str
    ranking: list[InsurerRankOut]
