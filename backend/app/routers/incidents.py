import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.user import AppUser, Incident, Evidence, UserPolicy
from app.models.kb import RequiredDocStd
from app.models.analysis import AnalysisRun, ValidationRule, ValidationResult
from app.models.question import QuestionBank, UserQuestionLog
from app.routers.auth import get_current_user_optional, verify_owner
from app.schemas import (
    IncidentCreate, IncidentAnalysisOut, PendingQuestionOut, AnswerIn,
    ChecklistOut, ChecklistItemOut, EvidenceIn, ClauseOut, ValidationResultOut,
)
from app.services.nlu import get_nlu_engine, ExtractedField
from app.services.claim_review import (
    merge_incident_fields, generate_claim_findings, pending_questions, iter_relevant_user_coverages,
)
from app.services.finding_persistence import persist_findings, load_findings_out
from app.services.validation import run_core_validation, persist_validation, check_docs_not_secured
from app.services.deletion import delete_incident_cascade
from app.models.kb import CoverageDocMap

router = APIRouter(prefix="/incidents", tags=["incidents"])

_NEGATIVE_MARKERS = ["아니", "안 ", "안했", "못", "없"]
BOOLEAN_FIELDS = {"hospitalized", "surgery", "local_treatment", "returned_home"}


def _serialize_structured(merged: dict[str, ExtractedField]) -> dict:
    return {
        name: {"value": f.value, "confidence": f.confidence, "source_span": f.source_span}
        for name, f in merged.items()
    }


def _apply_to_incident(incident: Incident, merged: dict[str, ExtractedField]):
    for name in ("country", "cause", "injury_part", "diagnosis", "hospitalized", "surgery",
                  "local_treatment", "returned_home"):
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


def _run_analysis(db: Session, incident: Incident, merged: dict[str, ExtractedField]) -> IncidentAnalysisOut:
    run = AnalysisRun(
        user_id=incident.user_id,
        run_type="사고후검토",
        incident_id=incident.incident_id,
    )
    db.add(run)
    db.flush()

    finding_specs = generate_claim_findings(db, incident.user_id, merged, incident.user_policy_id)
    findings_out = persist_findings(db, run, finding_specs)

    questions = pending_questions(db, merged)

    validation_specs = run_core_validation(db, incident.user_id, incident.occurred_at, merged)
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

    nlu = get_nlu_engine()
    explicit = {
        "country": payload.country, "cause": payload.cause, "injury_part": payload.injury_part,
        "diagnosis": payload.diagnosis, "hospitalized": payload.hospitalized, "surgery": payload.surgery,
        "local_treatment": payload.local_treatment, "returned_home": payload.returned_home,
        "medical_cost": payload.medical_cost,
    }
    merged = merge_incident_fields(nlu, payload.free_text, explicit)

    incident = Incident(
        user_id=payload.user_id,
        trip_id=payload.trip_id,
        user_policy_id=payload.user_policy_id,
        occurred_at=payload.occurred_at,
        medical_cost=payload.medical_cost,
    )
    _apply_to_incident(incident, merged)
    db.add(incident)
    db.flush()
    db.commit()
    db.refresh(incident)

    return _run_analysis(db, incident, merged)


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
    questions = pending_questions(db, merged)

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

    latest_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.incident_id == incident_id)
        .order_by(AnalysisRun.analysis_run_id.desc())
        .first()
    )
    db.add(UserQuestionLog(
        analysis_run_id=latest_run.analysis_run_id if latest_run else None,
        question_id=question.question_id,
        answer_text=payload.answer_text,
    ))

    field = question.target_field
    if field in BOOLEAN_FIELDS:
        negated = any(m in payload.answer_text for m in _NEGATIVE_MARKERS)
        value = not negated
    else:
        value = payload.answer_text

    explicit = {
        "country": incident.country, "cause": incident.cause, "injury_part": incident.injury_part,
        "diagnosis": incident.diagnosis, "hospitalized": incident.hospitalized, "surgery": incident.surgery,
        "local_treatment": incident.local_treatment, "returned_home": incident.returned_home,
        "medical_cost": incident.medical_cost,
    }
    explicit[field] = value
    nlu = get_nlu_engine()
    merged = merge_incident_fields(nlu, "", explicit)
    if field == "medical_cost":
        incident.medical_cost = value

    _apply_to_incident(incident, merged)
    db.flush()
    db.commit()
    db.refresh(incident)

    return _run_analysis(db, incident, merged)


def _current_merged(incident: Incident) -> dict[str, ExtractedField]:
    explicit = {
        "country": incident.country, "cause": incident.cause, "injury_part": incident.injury_part,
        "diagnosis": incident.diagnosis, "hospitalized": incident.hospitalized, "surgery": incident.surgery,
        "local_treatment": incident.local_treatment, "returned_home": incident.returned_home,
        "medical_cost": incident.medical_cost,
    }
    return merge_incident_fields(get_nlu_engine(), "", explicit)


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
    for uc, cov, insurer in iter_relevant_user_coverages(db, incident.user_id, merged, incident.user_policy_id):
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

    return ChecklistOut(incident_id=incident_id, items=items, validation_results=validation_results)


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
