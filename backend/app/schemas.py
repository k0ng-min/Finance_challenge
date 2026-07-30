import datetime as dt
from typing import Optional

from pydantic import BaseModel


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


class ClauseOut(BaseModel):
    clause_id: int
    article_no: str
    text: str
    page_ref: Optional[str]
    default_color: str
    highlight_color: str
    highlight_spans: Optional[list[HighlightSpanOut]] = None

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
    policy_type: str  # 직접가입/카드부가/단체
    period_start: dt.date
    period_end: dt.date
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
    policy_type: str
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
