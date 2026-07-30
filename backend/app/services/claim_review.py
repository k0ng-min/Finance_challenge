"""
사고 후 청구 검토 규칙 엔진 (ne.md 6.2/6.3, 9.2 MVP 범위).

사용자가 등록한 보험(user_policy/user_coverage, Phase 5)과 사고정보를 결합해
청구 검토가 필요한 담보 후보와 필요서류를 찾는다. KB에 정확히 매칭된 담보(coverage_id
있음)만 다루며, 매칭되지 않은 등록 담보는 근거가 없으므로 청구 대상으로 올리지 않는다.

사고내용 자유서술 구조화는 app.services.nlu의 NLUEngine에 위임한다(추후 경량 모델 교체 지점).
"""
from dataclasses import fields as dc_fields

from sqlalchemy.orm import Session

from app.models.kb import Clause, CoverageDocMap
from app.models.user import UserCoverage, UserPolicy
from app.models.question import QuestionBank
from app.services.nlu import NLUEngine, ExtractedField, IncidentDraft

# 사고 내용상 항상 검토 대상인 기본 담보 + 입원/수술이 있을 때만 검토 대상에 추가되는 담보
BASE_RELEVANT_STD_CODES = {"OVS_INJ_MED", "DEATH_INJURY"}
HOSPITALIZATION_TRIGGERED_STD_CODES = {"RESCUE"}


def merge_incident_fields(nlu: NLUEngine, free_text: str, explicit: dict) -> dict[str, ExtractedField]:
    """explicit(사용자가 명시적으로 입력한 값)이 있으면 confidence=1.0으로 우선하고,
    없는 필드만 자유서술(free_text)에서 NLU로 채운다."""
    draft = nlu.structure_incident(free_text or "")
    merged: dict[str, ExtractedField] = {}
    for f in dc_fields(IncidentDraft):
        name = f.name
        explicit_value = explicit.get(name)
        if explicit_value is not None:
            merged[name] = ExtractedField(value=explicit_value, confidence=1.0, source_span="user_input")
        else:
            merged[name] = getattr(draft, name)
    # medical_cost는 incident 테이블의 컬럼이지만 IncidentDraft(자유서술 구조화 대상)에는 없다.
    # 규칙기반 NLU로 금액을 추출하지 않으므로, 명시 입력이 없으면 항상 '모름'으로 두고
    # 능동 질문 대상에 포함시킨다.
    medical_cost = explicit.get("medical_cost")
    merged["medical_cost"] = (
        ExtractedField(value=medical_cost, confidence=1.0, source_span="user_input")
        if medical_cost else ExtractedField(value=None, confidence=0.0)
    )
    return merged


def relevant_std_codes(merged: dict[str, ExtractedField]) -> set[str]:
    codes = set(BASE_RELEVANT_STD_CODES)
    if merged["hospitalized"].value or merged["surgery"].value:
        codes |= HOSPITALIZATION_TRIGGERED_STD_CODES
    return codes


def iter_relevant_user_coverages(
    db: Session, user_id: int, merged: dict[str, ExtractedField], user_policy_id: int | None = None
):
    """사고와 관련 가능성이 있는(std_code 기준) 사용자의 KB매칭 담보를 (user_coverage, coverage, insurer)로 순회.
    user_policy_id가 지정되면 그 보험 하나만, 없으면(예: 과거 데이터·미선택) 등록된 보험 전체를 대상으로 한다."""
    codes = relevant_std_codes(merged)
    query = (
        db.query(UserCoverage)
        .join(UserPolicy, UserCoverage.user_policy_id == UserPolicy.user_policy_id)
        .filter(UserPolicy.user_id == user_id, UserCoverage.coverage_id.isnot(None))
    )
    if user_policy_id is not None:
        query = query.filter(UserPolicy.user_policy_id == user_policy_id)
    rows = query.all()
    for uc in rows:
        cov = uc.coverage
        if not cov or not cov.coverage_std or cov.coverage_std.std_code not in codes:
            continue
        yield uc, cov, cov.policy_version.product.insurer


def generate_claim_findings(
    db: Session, user_id: int, merged: dict[str, ExtractedField], user_policy_id: int | None = None
) -> list[dict]:
    findings: list[dict] = []
    unmatched_query = (
        db.query(UserCoverage)
        .join(UserPolicy, UserCoverage.user_policy_id == UserPolicy.user_policy_id)
        .filter(UserPolicy.user_id == user_id, UserCoverage.coverage_id.is_(None))
    )
    if user_policy_id is not None:
        unmatched_query = unmatched_query.filter(UserPolicy.user_policy_id == user_policy_id)
    unmatched_count = unmatched_query.count()

    for uc, cov, insurer in iter_relevant_user_coverages(db, user_id, merged, user_policy_id):
        def_clauses = (
            db.query(Clause)
            .filter(Clause.coverage_id == cov.coverage_id, Clause.clause_type == "보장정의")
            .all()
        )
        if not def_clauses:
            continue  # 근거 없이 청구 후보로 올리지 않음

        # 사고 시 "얼마나 보장되는지"가 가장 궁금한 부분이므로 별도 필드로 뽑아둔다(카드에
        # 배지로 짧게 보여주기 위함). 실제 가입금액(사용자 입력)을 우선하고 없으면 약관상
        # 보장한도 원문을 그대로 쓴다 — 둘 다 실제 데이터이며 지어낸 숫자는 넣지 않는다.
        coverage_amount = uc.subscribed_amount or cov.limit_amount

        findings.append({
            "finding_type": "추천담보",
            "status": "청구검토후보",
            "target_ref": f"{uc.user_policy.insurer_name_raw} - {cov.raw_name}",
            "insurer_code": insurer.code,
            "insurer_name": insurer.name,
            "description": (
                f"[{insurer.name}] 등록하신 '{cov.raw_name}' 담보가 이번 사고 내용과 관련될 가능성이 있어 "
                "청구 검토를 권장합니다. 실제 지급 여부는 보험회사 심사 결과에 따릅니다."
            ),
            "coverage_amount": coverage_amount,
            "confidence": "높음",
            "evidence": [(c, c.default_color) for c in def_clauses],
        })

        doc_maps = (
            db.query(CoverageDocMap)
            .filter(CoverageDocMap.coverage_id == cov.coverage_id)
            .all()
        )
        if doc_maps:
            mandatory = [dm.required_doc_std.doc_name for dm in doc_maps if dm.is_mandatory]
            optional = [dm.required_doc_std.doc_name for dm in doc_maps if not dm.is_mandatory]
            desc_parts = []
            if mandatory:
                desc_parts.append("필수 서류: " + ", ".join(mandatory))
            if optional:
                desc_parts.append("상황에 따라 필요할 수 있는 서류: " + ", ".join(optional))
            # 담보x서류 매핑이 여러 건이라도 근거 조항은 보통 동일한 제7조(청구) 하나이므로 중복 제거.
            seen_clause_ids: set[int] = set()
            evidence = []
            for dm in doc_maps:
                if dm.clause and dm.clause.clause_id not in seen_clause_ids:
                    seen_clause_ids.add(dm.clause.clause_id)
                    evidence.append((dm.clause, dm.clause.default_color))
            findings.append({
                "finding_type": "필요서류",
                "status": "서류확보필요",
                "target_ref": f"{uc.user_policy.insurer_name_raw} - {cov.raw_name}",
                "insurer_code": insurer.code,
                "insurer_name": insurer.name,
                "description": f"[{insurer.name}] {cov.raw_name} 청구 시 " + " / ".join(desc_parts),
                "confidence": "높음",
                "evidence": evidence,
            })

    if unmatched_count:
        findings.append({
            "finding_type": "보장공백",
            "status": "확인불가",
            "target_ref": "등록보험 중 KB 미매칭 담보",
            "insurer_code": None,
            "insurer_name": None,
            "description": (
                f"등록하신 보험 중 {unmatched_count}개 담보는 시스템 KB와 매칭되지 않아 이번 사고와의 "
                "관련성을 판단할 근거가 없습니다. 보험회사에 직접 확인이 필요합니다."
            ),
            "confidence": None,
            "evidence": [],
        })

    return findings


def pending_questions(db: Session, merged: dict[str, ExtractedField], confidence_threshold: float = 0.6):
    missing_fields = [
        name for name, f in merged.items()
        if f.value is None or f.confidence < confidence_threshold
    ]
    if not missing_fields:
        return []
    return (
        db.query(QuestionBank)
        .filter(QuestionBank.context_type == "사고후", QuestionBank.target_field.in_(missing_fields))
        .order_by(QuestionBank.impact_weight.desc())
        .all()
    )
