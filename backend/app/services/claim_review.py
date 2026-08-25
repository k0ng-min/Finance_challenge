"""
사고 후 청구 검토 규칙 엔진 (ne.md 6.2/6.3, 9.2 MVP 범위).

사용자가 등록한 보험(user_policy/user_coverage, Phase 5)과 사고정보를 결합해
청구 검토가 필요한 담보 후보와 필요서류를 찾는다. KB에 정확히 매칭된 담보(coverage_id
있음)만 다루며, 매칭되지 않은 등록 담보는 근거가 없으므로 청구 대상으로 올리지 않는다.

담보 판단 축(Phase 2, incident_type 기반):
예전엔 담보코드(OVS_INJ_MED/DEATH_INJURY/...)를 하드코딩하고 키워드 휴리스틱
(item_related/has_injury_signal)으로 "이 사고에 이 담보가 걸리나"를 그때그때 판단했다.
이제는 사고를 incident_type(L1/L2)으로 먼저 분류(app.services.incident_classify_gemini)
하고, 그 유형에 실제로 매핑된 조항(clause_incident_map)을 가진 담보만 후보로 올린다.
담보가 늘어나도(=사고유형을 더 채워도) 이 파일의 분기가 늘어나지 않는 게 핵심이다.
매핑은 조항 단위(=보험사별 실제 원문 단위)라서 보험사마다 다른 결과가 자연스럽게 유지된다
(메리츠 구조송환 조항처럼 문구가 없으면 그 보험사만 매핑에서 빠진다).

item_damage_type(도난/파손/분실, nlu.py의 정식 NLU 필드)은 유지한다 — 이건 폐기 대상이던
"키워드로 담보를 정하는 로직"이 아니라 사용자 답변을 정규화하는 별도 축이고, 사고가
상해+휴대품처럼 두 유형에 걸칠 때 분류된 주(主) incident_type 하나만으로는 놓치는 쪽을
보완하기 위해 보조 유형으로 계속 사용한다.

사고내용 자유서술 구조화는 app.services.nlu의 NLUEngine에 위임한다(추후 경량 모델 교체 지점).
"""
import json
from dataclasses import fields as dc_fields

from sqlalchemy.orm import Session

from app.models.kb import Clause, ClauseIncidentMap, CoverageDocMap, IncidentType
from app.models.user import Incident, UserCoverage, UserPolicy
from app.models.question import QuestionBank, UserQuestionLog
from app.services import incident_classify_gemini as incident_classify
from app.services import incident_questions_gemini
from app.services.coverage_amounts import amount_for_std_code
from app.services.incident_context import build_incident_context
from app.services.nlu import NLUEngine, ExtractedField, IncidentDraft, get_nlu_engine

_RELEVANCE_ORDER = {"직접": 0, "조건부": 1, "면책": 2}
_ITEM_DAMAGE_L2 = {"도난": "PROP_THEFT", "파손": "PROP_DAMAGE", "분실": "PROP_LOSS"}


def merge_incident_fields(
    nlu: NLUEngine, free_text: str, explicit: dict, *, classify_text: str | None = None
) -> dict[str, ExtractedField]:
    """explicit(사용자가 명시적으로 입력한 값)이 있으면 confidence=1.0으로 우선하고,
    없는 필드만 자유서술(free_text)에서 NLU로 채운다.

    classify_text: 이미 구조화가 끝난 사고를 다시 조회할 때(예: 체크리스트 재조회)는 NLU를
    또 호출하지 않기 위해 free_text=""로 두고 저장해둔 원문만 이 인자로 따로 넘긴다."""
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


def _item_damage_type_id(db: Session, item_damage_type: str | None) -> int | None:
    l2 = _ITEM_DAMAGE_L2.get(item_damage_type or "")
    if not l2:
        return None
    row = db.query(IncidentType).filter_by(l2_code=l2).first()
    return row.type_id if row else None


def resolve_type_ids(db: Session, incident_type_id: int | None, merged: dict[str, ExtractedField]) -> list[int]:
    """이번 사고에서 담보를 찾아야 하는 incident_type_id 목록.

    분류된 주 유형(incident_type_id) 하나가 기본이고, item_damage_type이 확인됐는데 주
    유형이 PROP 계열이 아니면(=상해+휴대품 혼합 사고) 그 유형도 추가한다.

    주 유형이 L1 루트면(=세부유형이 확신 없어 보류된 상태) 그 아래 세부유형을 전부
    같이 본다. 조항 매핑은 전부 L2에 달려 있어서, 루트 하나만으로는 걸리는 조항이
    0건이다 — "다리를 다쳤어요"가 상해까지만 잡혔을 때 KB에 상해 약관이 그대로 있는데도
    "관련 약관을 찾지 못했다"가 나오던 원인이다. 세부유형이 확정된 경우에는 형제 유형을
    끌어오지 않는다(상관없는 담보가 청구검토 후보로 섞인다)."""
    type_ids: list[int] = []
    if incident_type_id is not None:
        type_ids.append(incident_type_id)
        node = db.get(IncidentType, incident_type_id)
        if node is not None and node.parent_id is None:
            children = (
                db.query(IncidentType)
                .filter(IncidentType.parent_id == incident_type_id, IncidentType.is_active.is_(True))
                .order_by(IncidentType.type_id)
                .all()
            )
            type_ids.extend(c.type_id for c in children)
    item_field = merged.get("item_damage_type")
    item_type_id = _item_damage_type_id(db, item_field.value if item_field else None)
    if item_type_id is not None and item_type_id not in type_ids:
        type_ids.append(item_type_id)
    return type_ids


def _activity_matches_waiver(clause_text: str, modifiers: dict | None) -> bool:
    """수식자(활동)이 이 면책 조항 원문에 실제로 언급돼 있는지 확인한다.

    예: incident.modifiers.activity="스쿠버다이빙"이고 면책 조항 원문에 "스쿠버다이빙"이
    문자 그대로 있으면 True. 이게 없으면 담보 하나에 '직접'(보장정의)과 '면책' 조항이
    같이 걸려있을 때 무조건 '직접'을 대표값으로 써서, 실제로는 면책 대상인 사고(예:
    스쿠버다이빙 중 사망)도 "청구검토후보"로 과하게 낙관적으로 뜨는 문제가 있었다."""
    activity = (modifiers or {}).get("activity")
    if not activity or not clause_text:
        return False
    return activity.strip() in clause_text


def rank_maps(maps: list["ClauseIncidentMap"], modifiers: dict | None) -> list["ClauseIncidentMap"]:
    """관련도 순으로 정렬한다. 기본은 직접 > 조건부 > 면책이지만, 수식자(활동)이 실제로
    그 면책 조항 원문에 언급돼 있으면 그 면책 조항을 맨 앞으로 — '직접'이 같이 걸려있어도
    이번 사고엔 면책이 실제로 적용될 근거가 있으므로 면책을 대표값으로 쓴다.

    사고 시뮬레이션(services/simulation.py)도 이 함수를 그대로 호출한다. 가입 전 화면과
    사고 접수 화면의 판정 기준이 갈라지지 않게 하려면 정렬 규칙이 한 군데에만 있어야 한다."""
    def sort_key(m):
        if m.relevance == "면책" and _activity_matches_waiver(m.clause.text, modifiers):
            return (-1, 0)
        return (0, _RELEVANCE_ORDER.get(m.relevance, 99))
    return sorted(maps, key=sort_key)


def relevant_coverages_for_type(
    db: Session, type_id: int, user_id: int, user_policy_id: int | None = None,
    modifiers: dict | None = None,
):
    """type_id에 실제로 매핑된 조항(clause_incident_map)을 가진, 사용자가 등록한 담보를
    (user_coverage, coverage, insurer, relevance) 로 순회. relevance는 그 담보 안에서
    가장 강한 것(직접 > 조건부 > 면책, 단 활동 수식자가 면책 조항과 실제로 일치하면 그
    면책을 우선)을 대표값으로 쓴다.

    조항이 특정 보험사의 특정 PolicyVersion에 속하므로, 이 매칭은 보험사별로 독립적으로
    성립한다(다른 보험사가 같은 유형에 매핑 안 됐어도 이 보험사 결과에는 영향 없음)."""
    if type_id is None:
        return
    query = (
        db.query(UserCoverage)
        .join(UserPolicy, UserCoverage.user_policy_id == UserPolicy.user_policy_id)
        .filter(UserPolicy.user_id == user_id, UserCoverage.coverage_id.isnot(None))
    )
    if user_policy_id is not None:
        query = query.filter(UserPolicy.user_policy_id == user_policy_id)

    for uc in query.all():
        cov = uc.coverage
        if not cov:
            continue
        maps = (
            db.query(ClauseIncidentMap)
            .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
            .filter(Clause.coverage_id == cov.coverage_id, ClauseIncidentMap.type_id == type_id)
            .all()
        )
        if not maps:
            continue
        best = rank_maps(maps, modifiers)[0]
        yield uc, cov, cov.policy_version.product.insurer, best.relevance


def _evidence_clauses(db: Session, coverage_id: int, type_id: int, modifiers: dict | None = None) -> list[Clause]:
    maps = (
        db.query(ClauseIncidentMap)
        .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
        .filter(Clause.coverage_id == coverage_id, ClauseIncidentMap.type_id == type_id)
        .all()
    )
    ranked = rank_maps(maps, modifiers)
    seen: set[int] = set()
    clauses: list[Clause] = []
    for m in ranked:
        if m.clause_id in seen:
            continue
        seen.add(m.clause_id)
        clauses.append(m.clause)
    return clauses


def iter_relevant_user_coverages(
    db: Session, user_id: int, incident_type_id: int | None, merged: dict[str, ExtractedField],
    user_policy_id: int | None = None,
):
    """사고와 관련된(incident_type 기준) 사용자의 KB매칭 담보를 (user_coverage, coverage, insurer)로 순회.
    필요서류 체크리스트(get_checklist)처럼 relevance 구분 없이 "관련 담보 전체"가 필요할 때 쓴다."""
    seen_coverage_ids: set[int] = set()
    for type_id in resolve_type_ids(db, incident_type_id, merged):
        for uc, cov, insurer, _relevance in relevant_coverages_for_type(db, type_id, user_id, user_policy_id):
            if cov.coverage_id in seen_coverage_ids:
                continue
            seen_coverage_ids.add(cov.coverage_id)
            yield uc, cov, insurer


def generate_claim_findings(
    db: Session, incident: Incident, merged: dict[str, ExtractedField],
) -> list[dict]:
    """incident_type(직접/조건부/면책)로 찾은 담보마다 finding을 만든다.

    각 finding의 description에는 Gemini가 이 사고 내용에 맞춰 조항/서류를 설명한 문장을
    한 문장 덧붙인다(explain_clause_plain/explain_docs_for_incident). 실패해도(쿼터 초과 등)
    예외를 삼키고 기본 설명만 쓰므로 흐름은 죽지 않는다 — description은 기존과 같은 자유
    텍스트 필드라 프론트/스키마 변경 없이 그대로 들어간다."""
    user_id, user_policy_id, incident_type_id = incident.user_id, incident.user_policy_id, incident.type_id
    context = build_incident_context(db, incident)
    nlu = get_nlu_engine()
    modifiers = json.loads(incident.modifiers) if incident.modifiers else {}

    findings: list[dict] = []
    unmatched_query = (
        db.query(UserCoverage)
        .join(UserPolicy, UserCoverage.user_policy_id == UserPolicy.user_policy_id)
        .filter(UserPolicy.user_id == user_id, UserCoverage.coverage_id.is_(None))
    )
    if user_policy_id is not None:
        unmatched_query = unmatched_query.filter(UserPolicy.user_policy_id == user_policy_id)
    unmatched_count = unmatched_query.count()

    type_ids = resolve_type_ids(db, incident_type_id, merged)
    seen_coverage_ids: set[int] = set()

    for type_id in type_ids:
        for uc, cov, insurer, relevance in relevant_coverages_for_type(db, type_id, user_id, user_policy_id, modifiers):
            if cov.coverage_id in seen_coverage_ids:
                continue
            seen_coverage_ids.add(cov.coverage_id)

            evidence_clauses = _evidence_clauses(db, cov.coverage_id, type_id, modifiers)
            # 사고 시 "얼마나 보장되는지"가 가장 궁금한 부분이라 카드에 배지로 따로 뽑는다.
            # 값의 출처가 둘인데 성격이 달라서 한 칸에 섞지 않는다.
            #
            #  * coverage_amount — 약관이 정한 보장한도 원문. "1일 70,000원(20일 한도)"처럼
            #    등급과 무관한 조건이 붙는 경우가 있어 그대로 인용한다. 다만 대부분의 담보는
            #    금액을 "보험증권 기재 금액"이라고만 쓰고 증권으로 미룬다 — 그래서 이 칸만
            #    보면 정작 숫자가 없다.
            #  * plan_amount — 등록할 때 고른 등급의 실제 가입금액(보험사 공시표). 숫자는
            #    여기 있다. 등급을 안 골랐으면 비고, 지어내지 않는다.
            coverage_amount = uc.subscribed_amount or cov.limit_amount
            plan_amount = amount_for_std_code(
                db,
                insurer_code=insurer.code,
                plan_name=uc.user_policy.plan_name,
                std_code=cov.coverage_std.std_code if cov.coverage_std else None,
            )

            # 조항 원문을 이 사고 상황에 대입해 한 문장 설명(있으면 덧붙이고, 실패/무관하면
            # 조용히 생략 — explain_clause_plain은 실패 시 원문을 그대로 돌려주므로 그 경우엔
            # "원문과 동일"해서 아래 조건에서 자연히 걸러진다).
            situational = ""
            if evidence_clauses:
                explained = nlu.explain_clause_plain(evidence_clauses[0].text, context or None)
                if explained and explained.strip() and explained.strip() != evidence_clauses[0].text.strip():
                    situational = " " + explained.strip()

            if relevance == "면책":
                findings.append({
                    "finding_type": "제한조건",
                    "status": "보장 어려움",
                    "target_ref": f"{uc.user_policy.insurer_name_raw} - {cov.raw_name}",
                    "insurer_code": insurer.code,
                    "insurer_name": insurer.name,
                    "description": (
                        f"[{insurer.name}] 등록하신 '{cov.raw_name}' 담보는 약관상 이번 사고 유형을 "
                        "보상하지 않는(면책) 것으로 보입니다. 아래 실제 면책 조항을 확인해 주세요."
                        f"{situational}"
                    ),
                    "coverage_amount": coverage_amount,
                    "plan_amount": plan_amount,
                    "confidence": "높음",
                    "evidence": [(c, c.default_color) for c in evidence_clauses],
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
                        f"{situational}"
                    ),
                    "coverage_amount": coverage_amount,
                    "plan_amount": plan_amount,
                    "confidence": "높음",
                    "evidence": [(c, c.default_color) for c in evidence_clauses],
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
                doc_evidence = []
                for dm in doc_maps:
                    if dm.clause and dm.clause.clause_id not in seen_clause_ids:
                        seen_clause_ids.add(dm.clause.clause_id)
                        doc_evidence.append((dm.clause, dm.clause.default_color))

                doc_description = f"[{insurer.name}] {cov.raw_name} 청구 시 " + " / ".join(desc_parts)
                doc_explained = incident_classify.explain_docs_for_incident(mandatory + optional, context)
                if doc_explained:
                    doc_description += f" {doc_explained}"

                findings.append({
                    "finding_type": "필요서류",
                    "status": "서류확보필요",
                    "target_ref": f"{uc.user_policy.insurer_name_raw} - {cov.raw_name}",
                    "insurer_code": insurer.code,
                    "insurer_name": insurer.name,
                    "description": doc_description,
                    "confidence": "높음",
                    "evidence": doc_evidence,
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

    # 유형은 분류됐는데(=사고가 뭔지는 알겠는데) 위에서 아무 finding도 못 만들었다면(예: 등록된
    # 보험에 아직 해당 유형 관련 담보가 매핑되지 않은 경우) 왜 못 찾았는지 정직하게 안내한다.
    if type_ids and not findings:
        type_row = db.get(IncidentType, type_ids[0])
        type_name = type_row.name if type_row else "이번 사고"
        findings.append({
            "finding_type": "보장공백",
            "status": "확인불가",
            "target_ref": type_name,
            "insurer_code": None,
            "insurer_name": None,
            "description": (
                f"말씀하신 내용은 '{type_name}'에 가까워 보이지만, 등록하신 보험에서 관련 담보를 "
                "찾지 못했습니다. 실제로 가입돼 있는지 보험사에 직접 확인해 주세요."
            ),
            "confidence": None,
            "evidence": [],
        })

    return findings


def _matches_code(applies_to: str | None, code: str | None) -> bool:
    """applies_to=NULL이면 제한 없음. 값이 있으면(콤마로 여러 개 나열 가능) 지금 분류된
    코드가 그 안에 있을 때만 해당한다."""
    if applies_to is None:
        return True
    if not code:
        return False
    return code in {c.strip() for c in applies_to.split(",")}


def _question_applies(question: "QuestionBank", l1_code: str | None, l2_code: str | None) -> bool:
    """이 질문을 지금 사고에서 물어도 되는지.

    applies_to_l2가 달린 질문은 그 세부유형으로 확정됐을 때만 묻는다 — 아직 모르는 채로
    다 꺼내면 도난·파손·분실 질문이 한꺼번에 쏟아진다. applies_to_l1만 달린 질문은 그
    대분류 전체에서, 둘 다 없으면 모든 사고에서 후보가 된다."""
    if question.applies_to_l2 is not None:
        return _matches_code(question.applies_to_l1, l1_code) and _matches_code(question.applies_to_l2, l2_code)
    return _matches_code(question.applies_to_l1, l1_code)


# 생성 질문이 빼먹어도 공용 뱅크에서 반드시 보충하는 필드.
#
# item_damage_type은 이 모듈 자신이 휴대품 L2(도난/파손/분실)를 정하는 유일한 결정적
# 입력이다(_item_damage_type_id). 그런데 "분실"(본인 부주의)은 휴대품손해 특약에서
# 통째로 빠지는 보험사가 있어서, 이 한 값에 "청구검토 대상"과 "면책"이 갈린다.
# 모델이 그 사고에서만 중요한 걸 묻느라 이걸 지나칠 수 있는데, 여기는 모델의 재량에
# 맡길 자리가 아니다.
_MUST_ASK_FIELDS = {"item_damage_type"}


def _bank_candidates(db: Session, l1_code: str | None, l2_code: str | None = None) -> list[QuestionBank]:
    """공용 질문 뱅크(seed_questions.py)에서 이 대분류에 해당하는 질문을 꺼낸다.

    incident_id가 달린 행은 어떤 사고 하나를 위해 만들어진 것이므로 반드시 뺀다 —
    안 그러면 그 질문이 그 뒤로 모든 사람의 사고에 따라붙는다."""
    rows = (
        db.query(QuestionBank)
        .filter(QuestionBank.context_type == "사고후", QuestionBank.incident_id.is_(None))
        .order_by(QuestionBank.impact_weight.desc())
        .all()
    )
    return [q for q in rows if _question_applies(q, l1_code, l2_code)]


def _answered(question: QuestionBank, merged: dict[str, ExtractedField], modifiers: dict,
              confidence_threshold: float) -> bool:
    """이 질문에 이미 답이 있는지. 자유서술에서 뽑아낸 값도 답으로 친다."""
    field = question.target_field
    if field in merged:
        found = merged[field]
        return found.value is not None and found.confidence >= confidence_threshold
    return bool(modifiers.get(field))


def _answers_so_far(db: Session, incident_id: int) -> dict[str, str]:
    """이 사고에서 이미 받은 (질문 문장 → 답) 표.

    2단계 질문을 만들 때 이걸 그대로 넘긴다 — 안 넘기면 모델이 1단계와 똑같은 걸
    또 묻는다."""
    rows = (
        db.query(QuestionBank.question_text, UserQuestionLog.answer_text)
        .join(UserQuestionLog, UserQuestionLog.question_id == QuestionBank.question_id)
        .filter(QuestionBank.incident_id == incident_id)
        .all()
    )
    return {text: answer for text, answer in rows if answer}


def _staged_candidates(
    db: Session, incident: Incident, l1_code: str | None,
    merged: dict[str, ExtractedField], modifiers: dict, generate: bool,
    confidence_threshold: float,
) -> list[QuestionBank] | None:
    """사고별 맞춤 질문을 단계에 맞춰 꺼낸다.

    1단계(대분류 확인)를 다 답하기 전에는 1단계만 보여준다. 다 답하면 그때서야 그
    답을 읽고 2단계(세부유형) 질문을 만든다 — 두 단계를 한꺼번에 만들면 2단계가
    1단계 답을 못 보고, 결국 같은 걸 두 번 묻게 된다.

    어느 단계에서든 생성이 실패하면 None을 돌려 공용 뱅크로 되돌아간다."""
    gen = incident_questions_gemini
    first = gen.generate_questions(
        db, incident=incident, stage=gen.STAGE_L1, l1_code=l1_code, merged=merged,
        modifiers=modifiers, create=generate,
    )
    if first is None:
        return None
    if any(not _answered(q, merged, modifiers, confidence_threshold) for q in first):
        return first

    second = gen.generate_questions(
        db, incident=incident, stage=gen.STAGE_L2, l1_code=l1_code, merged=merged,
        modifiers=modifiers, answers=_answers_so_far(db, incident.incident_id),
        create=generate,
    )
    if second is None:
        return None
    return second


def pending_questions(
    db: Session, l1_code: str | None, merged: dict[str, ExtractedField],
    modifiers: dict | None = None, confidence_threshold: float = 0.6,
    incident: Incident | None = None, generate: bool = False,
    l2_code: str | None = None,
):
    """이 사고에서 아직 물어볼 게 남은 질문을 impact_weight 순으로 반환한다.

    질문은 두 곳에서 온다.

    1. **사고별 맞춤 질문** — 사고 내용을 읽고 그 자리에서 만든 것
       (incident_questions_gemini). 사고에 이미 적혀 있는 건 묻지 않고, 그 사고에서만
       중요한 것(예: 분실 장소가 잠겨 있었는지)을 묻는다. 이게 있으면 이걸 쓴다.
    2. **공용 질문 뱅크**(seed_questions.py, incident_id=NULL) — 1이 없을 때의 폴백.
       분류된 대분류(l1_code)에 태그된 것과 공통(applies_to_l1=NULL)만 후보가 된다.

    둘 다 question_bank 한 테이블에 들어 있어서, 공용 후보를 뽑을 때 incident_id가
    달린 행은 반드시 빼야 한다 — 안 그러면 어떤 사고에서 만들어진 질문이 그 뒤로 모든
    사람의 사고에 따라붙는다.

    incident를 넘기지 않으면 1을 아예 시도하지 않는다. generate=True는 저장까지 하는
    경로(분석 실행)에서만 켠다 — 조회 전용 경로는 커밋을 하지 않기 때문이다."""
    modifiers = modifiers or {}

    candidates = None
    if incident is not None:
        candidates = _staged_candidates(db, incident, l1_code, merged, modifiers, generate,
                                        confidence_threshold)

    if candidates is None:
        candidates = _bank_candidates(db, l1_code, l2_code)
    else:
        # 생성 질문을 쓰더라도 _MUST_ASK_FIELDS는 공용 뱅크에서 보충한다. 이미 그 필드를
        # 묻는 생성 질문이 있으면 겹쳐 넣지 않는다.
        asked = {q.target_field for q in candidates}
        supplement = [
            q for q in _bank_candidates(db, l1_code, l2_code)
            if q.target_field in _MUST_ASK_FIELDS and q.target_field not in asked
        ]
        if supplement:
            candidates = sorted(
                candidates + supplement, key=lambda q: -(q.impact_weight or 0.0)
            )

    pending = []
    for q in candidates:
        field = q.target_field
        if field in merged:
            f = merged[field]
            if f.value is not None and f.confidence >= confidence_threshold:
                continue
        elif modifiers.get(field):
            continue
        pending.append(q)
    return pending
