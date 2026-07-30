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

# 사고 내용상 상해 관련일 때 검토 대상인 기본 담보 + 입원/수술이 있을 때만 추가되는 담보.
# 휴대품(분실 제외) 손해가 확인되면 별도로 ITEM_STD_CODES를 더한다 — 아래 relevant_std_codes 참고.
BASE_RELEVANT_STD_CODES = {"OVS_INJ_MED", "DEATH_INJURY"}
HOSPITALIZATION_TRIGGERED_STD_CODES = {"RESCUE"}
ITEM_STD_CODES = {"PERSONAL_EFFECTS"}

# 사고가 휴대품(분실·도난·파손) 관련인지, 신체 상해 관련인지를 구분하는 키워드 신호.
# item_damage_type(NLU가 도난/파손/분실로 분류한 값)이 있으면 그걸 우선 쓰고, 없을 때만
# 이 키워드로 보조 판단한다 — 상해와 무관한 사고를 상해 담보에 잘못 붙이지 않기 위함이자,
# 반대로 휴대품손해(PERSONAL_EFFECTS, 실제 약관 있음)를 놓치지 않기 위함이다.
_ITEM_RELATED_KEYWORDS = [
    "분실", "잃어버", "잃었", "잊어버리고", "도난", "도둑맞", "소매치기", "훔쳐",
    "파손", "깨졌", "부서졌", "고장났", "고장 났", "망가졌",
]
_INJURY_HINT_KEYWORDS = [
    "다쳐", "다쳤", "부상", "골절", "통증", "아파", "아팠", "찢어", "화상", "출혈",
    "붓", "삐끗", "사망", "쓰러졌", "타박상", "염좌", "질병", "감염", "발열",
]


def _is_item_related(free_text: str, merged: dict[str, ExtractedField]) -> bool:
    if merged["item_damage_type"].value:
        return True
    text = free_text or ""
    return any(k in text for k in _ITEM_RELATED_KEYWORDS)


def _has_injury_signal(free_text: str, merged: dict[str, ExtractedField]) -> bool:
    # cause(사고 원인)는 여기서 신호로 안 쓴다 — NLU가 "휴대폰 분실"처럼 물건 관련
    # 사고에도 cause 필드를 채워버려서, cause만 보면 상해 여부를 구분하지 못한다.
    text = free_text or ""
    return bool(
        merged["injury_part"].value or merged["diagnosis"].value
        or merged["hospitalized"].value or merged["surgery"].value
        or any(k in text for k in _INJURY_HINT_KEYWORDS)
    )


def merge_incident_fields(
    nlu: NLUEngine, free_text: str, explicit: dict, *, classify_text: str | None = None
) -> dict[str, ExtractedField]:
    """explicit(사용자가 명시적으로 입력한 값)이 있으면 confidence=1.0으로 우선하고,
    없는 필드만 자유서술(free_text)에서 NLU로 채운다.

    classify_text: 분실/도난형 사고 판별용 원문. 보통 free_text와 같지만, 이미 구조화가
    끝난 사고를 다시 조회할 때(예: 체크리스트 재조회)는 NLU를 또 호출하지 않기 위해
    free_text=""로 두고 저장해둔 원문만 이 인자로 따로 넘긴다."""
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
    text_for_classification = classify_text if classify_text is not None else free_text
    merged["item_related"] = ExtractedField(
        value=_is_item_related(text_for_classification, merged), confidence=0.6, source_span=None,
    )
    merged["has_injury_signal"] = ExtractedField(
        value=_has_injury_signal(text_for_classification, merged), confidence=0.6, source_span=None,
    )
    return merged


def relevant_std_codes(merged: dict[str, ExtractedField]) -> set[str]:
    item_related = bool(merged.get("item_related") and merged["item_related"].value)
    has_injury = bool(merged.get("has_injury_signal") and merged["has_injury_signal"].value)
    codes: set[str] = set()
    if item_related:
        codes |= ITEM_STD_CODES
    if not item_related or has_injury:
        codes |= BASE_RELEVANT_STD_CODES
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

        # 휴대품손해(분실제외) 특약은 실제 약관상 "분실"은 명시적으로 면책 대상이다. 확실히
        # 분실로 확인된 경우엔 "청구해보세요"라고 안내하는 게 오히려 오해를 부르므로,
        # 상태/문구를 다르게 해서 왜 보장이 어려운지 먼저 알려준다(그래도 실제 면책 조항을
        # 그대로 근거로 첨부해서 사용자가 직접 확인할 수 있게 한다).
        is_plain_loss = (
            cov.coverage_std and cov.coverage_std.std_code == "PERSONAL_EFFECTS"
            and merged["item_damage_type"].value == "분실" and merged["item_damage_type"].confidence >= 0.5
        )
        if is_plain_loss:
            findings.append({
                "finding_type": "제한조건",
                "status": "보장 어려움",
                "target_ref": f"{uc.user_policy.insurer_name_raw} - {cov.raw_name}",
                "insurer_code": insurer.code,
                "insurer_name": insurer.name,
                "description": (
                    f"[{insurer.name}] 등록하신 '{cov.raw_name}' 담보는 약관상 '분실'(본인 부주의로 "
                    "잃어버린 경우)은 보상하지 않고, 도난·파손만 보상합니다. 말씀하신 내용은 단순 분실에 "
                    "가까워 보여 보장이 어려울 수 있습니다. 아래 실제 면책 조항을 확인해 주세요."
                ),
                "coverage_amount": coverage_amount,
                "confidence": "높음",
                "evidence": [(c, c.default_color) for c in def_clauses],
            })
        else:
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

    # 휴대품 관련 사고인데도 위에서 아무 finding도 못 만들었다면(예: 등록된 보험에 아직
    # 휴대품손해 담보가 매칭되지 않은 경우) 왜 못 찾았는지 정직하게 안내한다.
    item_related = bool(merged.get("item_related") and merged["item_related"].value)
    if item_related and not findings:
        findings.append({
            "finding_type": "보장공백",
            "status": "확인불가",
            "target_ref": "휴대품 손해(도난·파손, 분실 제외)",
            "insurer_code": None,
            "insurer_name": None,
            "description": (
                "말씀하신 내용은 휴대품 도난·파손·분실에 가까워 보이지만, 등록하신 보험에서 휴대품손해 "
                "담보를 찾지 못했습니다. 휴대품손해(분실제외) 특약에 실제로 가입돼 있는지 보험사에 "
                "직접 확인해 주세요."
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
    item_related = bool(merged.get("item_related") and merged["item_related"].value)
    has_injury = bool(merged.get("has_injury_signal") and merged["has_injury_signal"].value)
    if item_related and not has_injury:
        # 순수 물건 사고(상해 신호 없음) — 진단명/입원/수술 같은 상해 전용 질문은 무의미하다.
        # 대신 도난/파손/분실 중 무엇인지가 실제 보장 여부를 가르므로, 애매하면 그것만 묻는다.
        missing_fields = [f for f in missing_fields if f == "item_damage_type"]
    elif not item_related:
        # 상해 사고 — 휴대품 손해 유형 질문은 애초에 무관하다.
        missing_fields = [f for f in missing_fields if f != "item_damage_type"]
    # else(상해+휴대품 혼합): 두 종류 질문 모두 유의미하므로 그대로 둔다.
    if not missing_fields:
        return []
    return (
        db.query(QuestionBank)
        .filter(QuestionBank.context_type == "사고후", QuestionBank.target_field.in_(missing_fields))
        .order_by(QuestionBank.impact_weight.desc())
        .all()
    )
