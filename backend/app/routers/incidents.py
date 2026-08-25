import json
from dataclasses import fields as dc_fields
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.user import AppUser, Incident, Evidence, Trip, UserPolicy
from app.models.kb import RequiredDocStd, Insurer, IncidentType
from app.models.analysis import AnalysisRun, ValidationRule, ValidationResult
from app.models.question import QuestionBank, UserQuestionLog
from app.routers.auth import get_current_user_optional, verify_owner
from app.routers.policies import create_policy_for_user
from app.schemas import (
    IncidentCreate, IncidentAnalysisOut, PendingQuestionOut, AnswerIn,
    ChecklistOut, ChecklistItemOut, EvidenceIn, ClauseOut, ClauseTermOut, ValidationResultOut,
    IncidentTypeOut,
)
from app.services.nlu import get_nlu_engine, ExtractedField, IncidentDraft, classify_item_damage_type
from app.services import incident_classify_gemini as incident_classify
from app.services.claim_review import (
    merge_incident_fields, generate_claim_findings, pending_questions, iter_relevant_user_coverages,
)
from app.services.finding_persistence import persist_findings, load_findings_out
from app.services.validation import run_core_validation, persist_validation, check_docs_not_secured
from app.services.deletion import delete_incident_cascade, delete_trip_cascade
from app.models.kb import CoverageDocMap

router = APIRouter(prefix="/incidents", tags=["incidents"])

_NEGATIVE_MARKERS = ["아니", "안 ", "안했", "못", "없"]
BOOLEAN_FIELDS = {"hospitalized", "surgery", "local_treatment", "returned_home"}
_INCIDENT_DRAFT_FIELDS = {f.name for f in dc_fields(IncidentDraft)}


def _l1_code_for_type(db: Session, type_id: int | None) -> str | None:
    if type_id is None:
        return None
    type_row = db.get(IncidentType, type_id)
    return type_row.l1_code if type_row else None


def _modifiers_dict(incident: Incident) -> dict:
    return json.loads(incident.modifiers) if incident.modifiers else {}


_RECLASSIFY_CONFIDENCE_THRESHOLD = incident_classify.DEFAULT_L2_AUTO_THRESHOLD
_UNRESOLVED_L1_CODE = "UNRESOLVED"
_MAX_QUESTION_ROUNDS = 5


def _build_reclassification_text(
    free_text: str, merged: dict[str, ExtractedField], modifiers: dict,
    answered_questions: dict[str, str] | None = None,
) -> str:
    """최초 서술과 후속 답변을 L1 재분류용 단일 입력으로 만든다."""
    parts = [f"최초 사고 설명:\n{(free_text or '').strip() or '(없음)'}"]
    details = [
        f"{name}: {field.value}"
        for name, field in sorted(merged.items())
        if field.value is not None
    ]
    details.extend(
        f"{name}: {value}" for name, value in sorted(modifiers.items()) if value
    )
    details.extend(
        f"답변({name}): {value}"
        for name, value in sorted((answered_questions or {}).items()) if value
    )
    parts.append("추가 확인 정보:\n" + ("\n".join(details) if details else "(없음)"))
    return "\n\n".join(parts)


def _classify_incident(
    db: Session, free_text: str, merged: dict[str, ExtractedField],
    existing_type_id: int | None = None, existing_modifiers: dict | None = None,
    existing_confidence: float | None = None,
    answered_questions: dict[str, str] | None = None,
) -> tuple[int | None, float | None, dict]:
    """사고를 incident_type(L1→L2)으로 분류한다.

    existing_type_id가 없으면(=최초 접수) L1을 새로 분류하고 modifiers도 처음 추출한다.
    확정된 L2가 있으면 L1을 유지한다. L1 루트에 보류된 사고는 confidence와 무관하게 최초
    서술과 후속 답변을 합쳐 L1부터 다시 평가한다. 그래야 처음엔 L1이 그럴듯했더라도 새로
    확인된 정보가 다른 유형이면 기존 L1 안에서 L2만 고르는 고착을 막을 수 있다.

    이미 충분히 확신 있게 분류돼 있으면(existing_confidence 높음) 매 답변마다 다시 Gemini를
    부르지 않는다 — 무료 API 쿼터를 아끼기 위함이자, 이미 답이 정해진 걸 매번 다시 물어서
    결과가 흔들리는 걸 막기 위함이다."""
    modifiers = dict(existing_modifiers or {})
    existing_type = db.get(IncidentType, existing_type_id) if existing_type_id is not None else None
    existing_is_root = existing_type is not None and existing_type.parent_id is None
    if (
        existing_type is not None
        and not existing_is_root
        and (existing_confidence or 0.0) >= _RECLASSIFY_CONFIDENCE_THRESHOLD
    ):
        return existing_type_id, existing_confidence, modifiers
    if existing_type_id is None:
        l1_code, l1_confidence, _reason = incident_classify.classify_l1(free_text or "")
        modifiers.update(incident_classify.extract_modifiers(free_text or ""))
    elif existing_is_root:
        # L1은 확정됐지만 L2가 보류된 root도 후속 답변이 들어오면 다시 L1부터 본다.
        # 그래야 최초 L1 confidence가 높았더라도 새 정보가 명확히 다른 유형이면 고착되지 않는다.
        augmented_text = _build_reclassification_text(
            free_text, merged, modifiers, answered_questions,
        )
        l1_code, l1_confidence, _reason = incident_classify.classify_l1(augmented_text)
        modifiers.update(incident_classify.extract_modifiers(augmented_text))
    else:
        l1_code = _l1_code_for_type(db, existing_type_id)
        l1_confidence = existing_confidence or 0.0

    if not l1_code:
        return None, None, modifiers

    root = db.query(IncidentType).filter_by(l1_code=l1_code, parent_id=None).first()
    if l1_confidence < incident_classify.DEFAULT_L1_AUTO_THRESHOLD:
        # L1 신뢰도도 낮으면 L2 호출로 추측을 확대하지 않고, L1 루트에서 질문을 생성한다.
        return (root.type_id if root else None), l1_confidence, modifiers

    # 자유서술에 세 유형이 명시됐는데 NLU 구현이 저신뢰 값을 비운 경우에도 정규화 값을
    # incident.structured/item_damage_type까지 이어준다.
    normalized_item_damage = classify_item_damage_type(free_text) if l1_code == "PROP" else None
    item_field = merged.get("item_damage_type")
    if normalized_item_damage and (item_field is None or item_field.value is None):
        merged["item_damage_type"] = ExtractedField(
            value=normalized_item_damage,
            confidence=0.5 if normalized_item_damage == "분실" else 0.7,
            source_span="규칙 정규화",
        )

    answers = {name: str(f.value) for name, f in merged.items() if f.value is not None}
    answers.update({k: str(v) for k, v in modifiers.items() if v})
    answers.update({k: str(v) for k, v in (answered_questions or {}).items() if v})

    # PROP의 세 하위유형은 사용자가 능동질문에서 명시적으로 답한 정규화 값과 1:1이다.
    # 이 근거가 있으면 Gemini가 꺼져 있어도 다시 추측하거나 같은 질문을 반복하지 않는다.
    prop_l2_by_answer = {"도난": "PROP_THEFT", "파손": "PROP_DAMAGE", "분실": "PROP_LOSS"}
    if l1_code == "PROP":
        # 일부 NLU 구현은 자유서술의 저신뢰 "분실" 값을 구조화 결과에서 비울 수 있다.
        # 이 세 값은 별도 규칙 함수로도 동일하게 정규화해 명시 표현을 놓치지 않는다.
        item_damage_type = answers.get("item_damage_type")
        l2_code = prop_l2_by_answer.get(item_damage_type or "")
        if l2_code:
            l2_row = db.query(IncidentType).filter_by(l2_code=l2_code).first()
            if l2_row:
                return l2_row.type_id, 1.0, modifiers

    result = incident_classify.classify_l2(db, l1_code, free_text or "", answers)
    if result.l2_code:
        return result.type_id, result.confidence, modifiers
    # 신규 유형 제안도 검수 전에는 사고에 자동 할당하지 않는다. L1 루트에서 질문으로 보강한다.
    # root에서는 이 값이 L1의 확정도다. 후속 답변 때 root를 항상 재분류하므로 높은 값을
    # 보존해도 L1에 고착되지 않으며, 질문 엔진은 'L1 미확정'과 'L2만 보류'를 구분할 수 있다.
    return (root.type_id if root else None), l1_confidence, modifiers


def _answered_question_state(
    db: Session, incident_id: int,
) -> tuple[set[int], set[str], dict[str, str]]:
    """사고의 모든 분석 라운드에 걸친 답변 상태를 모은다.

    질문 로그는 답변 당시 analysis_run에 연결되므로 최신 run 하나만 보면 이전 답변을
    잃는다. incident_id로 모든 run을 조인해 질문 ID/목적 필드/원문 답변을 복원한다.
    """
    rows = (
        db.query(UserQuestionLog, QuestionBank)
        .join(AnalysisRun, UserQuestionLog.analysis_run_id == AnalysisRun.analysis_run_id)
        .join(QuestionBank, UserQuestionLog.question_id == QuestionBank.question_id)
        .filter(AnalysisRun.incident_id == incident_id)
        .order_by(UserQuestionLog.qlog_id.asc())
        .all()
    )
    question_ids: set[int] = set()
    target_fields: set[str] = set()
    answers: dict[str, str] = {}
    for log, question in rows:
        question_ids.add(question.question_id)
        if question.target_field:
            target_fields.add(question.target_field)
            if log.answer_text and log.answer_text.strip():
                answers[question.target_field] = log.answer_text.strip()
    return question_ids, target_fields, answers


def _pending_questions_for_incident(
    db: Session, incident: Incident, merged: dict[str, ExtractedField],
):
    """분류 확정도와 답변 이력을 함께 반영한 사고별 다음 질문 목록."""
    answered_ids, answered_fields, _ = _answered_question_state(db, incident.incident_id)
    if len(answered_ids) >= _MAX_QUESTION_ROUNDS:
        return []

    type_row = db.get(IncidentType, incident.type_id) if incident.type_id else None
    is_confirmed_l2 = (
        type_row is not None
        and type_row.parent_id is not None
        and (incident.classify_confidence or 0.0) >= _RECLASSIFY_CONFIDENCE_THRESHOLD
    )
    if is_confirmed_l2:
        return []

    is_unresolved_l1 = (
        type_row is None
        or (type_row.parent_id is None and (
            (incident.classify_confidence or 0.0) < incident_classify.DEFAULT_L1_AUTO_THRESHOLD
        ))
    )
    l1_code = _UNRESOLVED_L1_CODE if is_unresolved_l1 else type_row.l1_code
    return pending_questions(
        db, l1_code, merged, _modifiers_dict(incident),
        answered_question_ids=answered_ids,
        answered_target_fields=answered_fields,
    )


def _serialize_structured(merged: dict[str, ExtractedField]) -> dict:
    return {
        name: {"value": f.value, "confidence": f.confidence, "source_span": f.source_span}
        for name, f in merged.items()
    }


def _apply_to_incident(incident: Incident, merged: dict[str, ExtractedField]):
    for name in ("country", "cause", "injury_part", "diagnosis", "hospitalized", "surgery",
                  "local_treatment", "returned_home", "item_damage_type"):
        value = merged[name].value
        if value is not None:
            setattr(incident, name, value)
    incident.structured = json.dumps(_serialize_structured(merged), ensure_ascii=False)


def _linked_policy_names(incident: Incident) -> tuple[str | None, str | None, str | None]:
    if not incident.user_policy_id:
        return None, None, None
    policy = incident.user_policy
    if not policy:
        return None, None, None
    insurer_code = policy.product.insurer.code if policy.product else None
    insurer_name = policy.product.insurer.name if policy.product else policy.insurer_name_raw
    product_name = policy.product.name if policy.product else policy.product_name_raw
    return insurer_code, insurer_name, product_name


def _trip_context(incident: Incident) -> dict:
    """서류체크·실수방지·약관형광펜 화면에서 "이 사고가 어느 여행 건인지"를 한눈에 보여주기
    위한 컨텍스트. 연결된 여행(trip_id)이 있으면 그 목적지·기간을, 없으면(사고만 단독 접수한
    경우) 사고 접수 시 입력한 country만 보여준다 — 여행 기록과 사고 기록이 서로 무관하게
    따로 떠 보이던 문제를 없애기 위함."""
    trip = incident.trip if incident.trip_id else None
    return {
        "trip_id": incident.trip_id,
        "trip_destination": trip.destination if trip else None,
        "trip_start_date": trip.start_date.isoformat() if trip and trip.start_date else None,
        "trip_end_date": trip.end_date.isoformat() if trip and trip.end_date else None,
        "incident_country": incident.country,
    }


def _run_analysis(db: Session, incident: Incident, merged: dict[str, ExtractedField]) -> IncidentAnalysisOut:
    run = AnalysisRun(
        user_id=incident.user_id,
        run_type="사고후검토",
        incident_id=incident.incident_id,
    )
    db.add(run)
    db.flush()

    finding_specs = generate_claim_findings(db, incident, merged)
    findings_out = persist_findings(db, run, finding_specs)

    l1_code = _l1_code_for_type(db, incident.type_id)
    questions = _pending_questions_for_incident(db, incident, merged)

    validation_specs = run_core_validation(db, incident.user_id, incident.occurred_at, merged, l1_code)
    doc_check = check_docs_not_secured(db, incident.incident_id)
    if doc_check:
        validation_specs.append(doc_check)
    validation_out = persist_validation(db, run, validation_specs)

    run.result_summary = json.dumps(
        {"finding_count": len(finding_specs), "pending_question_count": len(questions)}, ensure_ascii=False
    )
    db.commit()

    insurer_code, insurer_name, product_name = _linked_policy_names(incident)
    return IncidentAnalysisOut(
        incident_id=incident.incident_id,
        analysis_run_id=run.analysis_run_id,
        structured=_serialize_structured(merged),
        findings=findings_out,
        pending_questions=[
            PendingQuestionOut(
                question_id=q.question_id, question_text=q.question_text,
                target_field=q.target_field, impact_weight=q.impact_weight,
            ) for q in questions
        ],
        validation_results=validation_out,
        linked_insurer_code=insurer_code,
        linked_insurer_name=insurer_name,
        linked_product_name=product_name,
        **_trip_context(incident),
    )


@router.post("", response_model=IncidentAnalysisOut)
@limiter.limit("20/minute")
def create_incident(
    request: Request, payload: IncidentCreate, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    verify_owner(payload.user_id, current)
    user = db.get(AppUser, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다. 먼저 /users로 사용자를 생성하세요.")

    # 게스트(비로그인)는 "여행 1개 + 거기 이어지는 보험 1개 + 사고 1개"만 들고 간다.
    # 새 사고를 접수하면 앞의 기록은 전부 정리한다 — 단, 이번 요청이 방금 만든 여행을
    # 가리키고 있다면(trip_id) 그건 이 흐름의 일부라 지우지 않는다.
    if current is None:
        keep_trip_id = payload.trip_id
        for old in db.query(Incident).filter(Incident.user_id == payload.user_id).all():
            delete_incident_cascade(db, old)
        for old_trip in db.query(Trip).filter(Trip.user_id == payload.user_id).all():
            if old_trip.trip_id != keep_trip_id:
                delete_trip_cascade(db, old_trip)

    # 연결할 여행이 없으면 사고 접수 화면에서 받은 목적지·기간으로 여행을 여기서 만들어준다.
    # "사고부터 접수한 사람"도 여행 기록이 남아야 나중에 서류체크·형광펜 화면에서 같은
    # 여행 맥락으로 이어서 볼 수 있다.
    trip_id = payload.trip_id
    if trip_id is None and payload.new_trip_destination:
        start = payload.new_trip_start_date or date.today()
        end = payload.new_trip_end_date or (start + timedelta(days=7))
        if end <= start:
            end = start + timedelta(days=1)
        new_trip = Trip(
            user_id=payload.user_id,
            destination=payload.new_trip_destination,
            start_date=start, end_date=end,
            purpose="사고 접수 중 등록",
        )
        db.add(new_trip)
        db.flush()
        trip_id = new_trip.trip_id

    user_policy_id = payload.user_policy_id
    # 여행에 이미 보험이 묶여 있으면 그걸 그대로 쓴다 — 여행만 고르면 보험이 따라오게 하는 핵심.
    if user_policy_id is None and trip_id is not None:
        linked_trip = db.get(Trip, trip_id)
        if linked_trip and linked_trip.user_policy_id:
            user_policy_id = linked_trip.user_policy_id

    if user_policy_id is None and payload.insurer_code:
        insurer = db.query(Insurer).filter(Insurer.code == payload.insurer_code).first()
        if not insurer:
            raise HTTPException(status_code=404, detail="알 수 없는 보험사예요.")
        today = date.today()
        policy = create_policy_for_user(
            db, user_id=payload.user_id, insurer_name_raw=insurer.name,
            period_start=today, period_end=today + timedelta(days=30),
        )
        user_policy_id = policy.user_policy_id

    # 이번에 고른 보험을 이 여행에도 묶어둔다 — 다음에 같은 여행으로 사고를 접수하면 자동 연결된다.
    if trip_id is not None and user_policy_id is not None:
        linked_trip = db.get(Trip, trip_id)
        if linked_trip and linked_trip.user_policy_id is None:
            linked_trip.user_policy_id = user_policy_id

    nlu = get_nlu_engine()
    explicit = {
        "country": payload.country, "cause": payload.cause, "injury_part": payload.injury_part,
        "diagnosis": payload.diagnosis, "hospitalized": payload.hospitalized, "surgery": payload.surgery,
        "local_treatment": payload.local_treatment, "returned_home": payload.returned_home,
        "medical_cost": payload.medical_cost,
    }
    merged = merge_incident_fields(nlu, payload.free_text, explicit)
    type_id, classify_confidence, modifiers = _classify_incident(db, payload.free_text, merged)

    incident = Incident(
        user_id=payload.user_id,
        trip_id=trip_id,
        user_policy_id=user_policy_id,
        occurred_at=payload.occurred_at,
        medical_cost=payload.medical_cost,
        free_text=payload.free_text,
        type_id=type_id,
        classify_confidence=classify_confidence,
        modifiers=json.dumps(modifiers, ensure_ascii=False) if modifiers else None,
    )
    _apply_to_incident(incident, merged)
    db.add(incident)
    db.flush()
    db.commit()
    db.refresh(incident)

    return _run_analysis(db, incident, merged)


@router.get("/types", response_model=list[IncidentTypeOut])
def list_incident_l1_types(db: Session = Depends(get_db)):
    """사고유형 대분류(L1) 8개 고정 목록. 여행 준비 단계에서 "관심 있는 사고유형"을 고르거나
    (내 여행 STEP4), 보험사 상세화면에서 그 유형에 맞는 약관을 조회할 때(insurers 라우터) 쓴다.
    /{incident_id}보다 먼저 등록해야 "/types"가 int로 파싱 시도되는 걸 막을 수 있다."""
    rows = db.query(IncidentType).filter(IncidentType.parent_id.is_(None)).order_by(IncidentType.type_id).all()
    return [IncidentTypeOut(type_id=t.type_id, l1_code=t.l1_code, name=t.name) for t in rows]


@router.get("/{incident_id}", response_model=IncidentAnalysisOut)
def get_incident(
    incident_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    """규칙엔진을 재실행하지 않고, 마지막 분석 결과를 그대로 조회한다 (페이지 재방문/새로고침용)."""
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="사고 정보를 찾을 수 없습니다.")
    verify_owner(incident.user_id, current)

    latest_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.incident_id == incident_id)
        .order_by(AnalysisRun.analysis_run_id.desc())
        .first()
    )
    if not latest_run:
        raise HTTPException(status_code=404, detail="아직 분석 결과가 없습니다.")

    findings_out = load_findings_out(db, latest_run.analysis_run_id)

    validation_rows = (
        db.query(ValidationResult)
        .join(ValidationRule, ValidationResult.rule_id == ValidationRule.rule_id)
        .filter(ValidationResult.analysis_run_id == latest_run.analysis_run_id)
        .all()
    )
    validation_out = [
        ValidationResultOut(
            rule_code=v.rule.rule_code, rule_name=v.rule.rule_name, severity=v.rule.severity,
            passed=v.passed, detail=v.detail,
        ) for v in validation_rows
    ]

    merged = _current_merged(incident)
    questions = _pending_questions_for_incident(db, incident, merged)

    return IncidentAnalysisOut(
        incident_id=incident.incident_id,
        analysis_run_id=latest_run.analysis_run_id,
        structured=_serialize_structured(merged),
        findings=findings_out,
        pending_questions=[
            PendingQuestionOut(
                question_id=q.question_id, question_text=q.question_text,
                target_field=q.target_field, impact_weight=q.impact_weight,
            ) for q in questions
        ],
        validation_results=validation_out,
        linked_insurer_code=_linked_policy_names(incident)[0],
        linked_insurer_name=_linked_policy_names(incident)[1],
        linked_product_name=_linked_policy_names(incident)[2],
        **_trip_context(incident),
    )


@router.post("/{incident_id}/answers", response_model=IncidentAnalysisOut)
@limiter.limit("30/minute")
def answer_question(
    request: Request, incident_id: int, payload: AnswerIn, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="사고 정보를 찾을 수 없습니다.")
    verify_owner(incident.user_id, current)
    question = db.get(QuestionBank, payload.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")

    answer_text = payload.answer_text.strip()
    if not answer_text:
        raise HTTPException(status_code=422, detail="답변을 입력해주세요.")

    # 오래 열린 탭이나 중복 클릭이 이미 해결된/무관한 질문을 다시 제출하지 못하게 한다.
    current_question_ids = {
        q.question_id for q in _pending_questions_for_incident(db, incident, _current_merged(incident))
    }
    if question.question_id not in current_question_ids:
        raise HTTPException(status_code=409, detail="이미 답했거나 현재 사고와 관련 없는 질문입니다.")

    latest_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.incident_id == incident_id)
        .order_by(AnalysisRun.analysis_run_id.desc())
        .first()
    )
    db.add(UserQuestionLog(
        analysis_run_id=latest_run.analysis_run_id if latest_run else None,
        question_id=question.question_id,
        answer_text=answer_text,
    ))

    field = question.target_field
    explicit = {
        "country": incident.country, "cause": incident.cause, "injury_part": incident.injury_part,
        "diagnosis": incident.diagnosis, "hospitalized": incident.hospitalized, "surgery": incident.surgery,
        "local_treatment": incident.local_treatment, "returned_home": incident.returned_home,
        "medical_cost": incident.medical_cost, "item_damage_type": incident.item_damage_type,
    }
    if field in BOOLEAN_FIELDS:
        negated = any(m in answer_text for m in _NEGATIVE_MARKERS)
        explicit[field] = not negated
    elif field == "item_damage_type":
        # 자유서술 답변("소매치기당했어요"/"그냥 잃어버렸어요" 등)을 도난/파손/분실 중
        # 하나로 정규화한다 — 원문 그대로 저장하면 claim_review.py가 정확히 비교할 수 없다.
        explicit[field] = classify_item_damage_type(answer_text)
    elif field in _INCIDENT_DRAFT_FIELDS or field == "medical_cost":
        explicit[field] = answer_text
        if field == "medical_cost":
            incident.medical_cost = answer_text
    else:
        # IncidentDraft에 없는 필드 — L2 판별 전용 질문(예: flight_delay_hours)이므로
        # incident.modifiers JSON에 직접 담는다. explicit/merged 경로로는 흐르지 않는다.
        current_modifiers = _modifiers_dict(incident)
        current_modifiers[field] = answer_text
        incident.modifiers = json.dumps(current_modifiers, ensure_ascii=False)

        # 중립 L1 확인 답변에서 휴대품 사고의 세부유형까지 명시됐다면 정규화 축에도
        # 함께 반영한다. 이후 PROP으로 재분류됐을 때 규칙 기반으로 L2를 확정할 수 있다.
        if field == "incident_type_detail":
            normalized_item_damage = classify_item_damage_type(answer_text)
            if normalized_item_damage:
                explicit["item_damage_type"] = normalized_item_damage

    nlu = get_nlu_engine()
    merged = merge_incident_fields(nlu, "", explicit, classify_text=incident.free_text)
    _apply_to_incident(incident, merged)

    db.flush()
    _, _, answered_questions = _answered_question_state(db, incident_id)
    type_id, classify_confidence, modifiers = _classify_incident(
        db, incident.free_text, merged,
        existing_type_id=incident.type_id, existing_modifiers=_modifiers_dict(incident),
        existing_confidence=incident.classify_confidence,
        answered_questions=answered_questions,
    )
    if type_id is not None:
        incident.type_id = type_id
        incident.classify_confidence = classify_confidence
    if modifiers:
        incident.modifiers = json.dumps(modifiers, ensure_ascii=False)

    db.flush()
    db.commit()
    db.refresh(incident)

    return _run_analysis(db, incident, merged)


def _current_merged(incident: Incident) -> dict[str, ExtractedField]:
    explicit = {
        "country": incident.country, "cause": incident.cause, "injury_part": incident.injury_part,
        "diagnosis": incident.diagnosis, "hospitalized": incident.hospitalized, "surgery": incident.surgery,
        "local_treatment": incident.local_treatment, "returned_home": incident.returned_home,
        "medical_cost": incident.medical_cost, "item_damage_type": incident.item_damage_type,
    }
    return merge_incident_fields(get_nlu_engine(), "", explicit, classify_text=incident.free_text)


@router.get("/{incident_id}/checklist", response_model=ChecklistOut)
def get_checklist(
    incident_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="사고 정보를 찾을 수 없습니다.")
    verify_owner(incident.user_id, current)

    merged = _current_merged(incident)
    evidence_by_doc = {
        e.required_doc_std_id: e for e in
        db.query(Evidence).filter(Evidence.incident_id == incident_id).all()
    }

    items: list[ChecklistItemOut] = []
    seen = set()
    for uc, cov, insurer in iter_relevant_user_coverages(db, incident.user_id, incident.type_id, merged, incident.user_policy_id):
        doc_maps = db.query(CoverageDocMap).filter(CoverageDocMap.coverage_id == cov.coverage_id).all()
        for dm in doc_maps:
            key = (dm.required_doc_std_id, cov.coverage_id)
            if key in seen:
                continue
            seen.add(key)
            doc: RequiredDocStd = dm.required_doc_std
            ev = evidence_by_doc.get(dm.required_doc_std_id)
            items.append(ChecklistItemOut(
                required_doc_std_id=doc.required_doc_std_id,
                doc_code=doc.doc_code,
                doc_name=doc.doc_name,
                acquire_location=doc.acquire_location,
                is_mandatory=dm.is_mandatory,
                coverage_target_ref=f"{uc.user_policy.insurer_name_raw} - {cov.raw_name}",
                insurer_name=insurer.name,
                status=ev.status if ev else "미확인",
                memo=ev.memo if ev else None,
                clause=ClauseOut(
                    clause_id=dm.clause.clause_id, article_no=dm.clause.article_no, text=dm.clause.text,
                    page_ref=dm.clause.page_ref, default_color=dm.clause.default_color,
                    highlight_color=dm.clause.default_color,
                    terms=[ClauseTermOut.model_validate(t) for t in dm.clause.terms],
                ) if dm.clause else None,
            ))

    doc_check = check_docs_not_secured(db, incident_id)
    validation_results = []
    if doc_check:
        rule = db.query(ValidationRule).filter_by(rule_code=doc_check["rule_code"]).first()
        if rule:
            validation_results.append(ValidationResultOut(
                rule_code=rule.rule_code, rule_name=rule.rule_name, severity=rule.severity,
                passed=doc_check["passed"], detail=doc_check["detail"],
            ))

    return ChecklistOut(
        incident_id=incident_id, items=items, validation_results=validation_results,
        **_trip_context(incident),
    )


@router.post("/{incident_id}/evidence", response_model=ChecklistOut)
def submit_evidence(
    incident_id: int, payload: list[EvidenceIn], db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="사고 정보를 찾을 수 없습니다.")
    verify_owner(incident.user_id, current)

    for item in payload:
        existing = (
            db.query(Evidence)
            .filter(Evidence.incident_id == incident_id, Evidence.required_doc_std_id == item.required_doc_std_id)
            .first()
        )
        if existing:
            existing.status = item.status
            existing.memo = item.memo
        else:
            db.add(Evidence(
                incident_id=incident_id, required_doc_std_id=item.required_doc_std_id,
                status=item.status, memo=item.memo,
            ))
    db.commit()

    return get_checklist(incident_id, db, current)


@router.delete("/{incident_id}")
def delete_incident(
    incident_id: int, db: Session = Depends(get_db),
    current: AppUser | None = Depends(get_current_user_optional),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="사고 정보를 찾을 수 없습니다.")
    verify_owner(incident.user_id, current)
    delete_incident_cascade(db, incident)
    db.commit()
    return {"status": "deleted"}
