"""
누락·모순 검증 규칙 엔진 (ne.md 11.2, new.md validation_rule/validation_result).
LLM을 쓰지 않는 결정적 로직만 둔다.
"""
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun, ValidationResult, ValidationRule
from app.models.user import UserPolicy
from app.schemas import ValidationResultOut
from app.services.nlu import ExtractedField


def check_period_mismatch(db: Session, user_id: int, occurred_at) -> dict | None:
    if not occurred_at:
        return None  # 사고일 자체가 없으면 판단 불가 (결과를 만들지 않음)
    policies = db.query(UserPolicy).filter(UserPolicy.user_id == user_id).all()
    dated_policies = [p for p in policies if p.period_start and p.period_end]
    if not dated_policies:
        return None  # 등록된 보험이 없으면 비교 대상이 없음
    occurred_date = occurred_at.date() if hasattr(occurred_at, "date") else occurred_at
    covered = [p for p in dated_policies if p.period_start <= occurred_date <= p.period_end]
    passed = len(covered) > 0
    if passed:
        detail = f"사고일({occurred_date})이 보험기간에 포함되는 등록보험 {len(covered)}건 확인됨."
    else:
        ranges = ", ".join(f"{p.insurer_name_raw}({p.period_start}~{p.period_end})" for p in dated_policies)
        detail = f"사고일({occurred_date})이 등록된 어떤 보험의 보험기간에도 포함되지 않습니다. 등록 보험기간: {ranges}"
    return {"rule_code": "PERIOD_MISMATCH", "passed": passed, "detail": detail}


def check_info_missing(merged: dict[str, ExtractedField]) -> dict:
    missing = [name for name, f in merged.items() if f.value is None or f.confidence < 0.6]
    passed = len(missing) == 0
    detail = f"미확인 항목: {', '.join(missing)}" if missing else "핵심 사고정보가 모두 확인되었습니다."
    return {"rule_code": "INFO_MISSING", "passed": passed, "detail": detail}


def check_surgery_hospitalized_contradiction(merged: dict[str, ExtractedField]) -> dict | None:
    surgery = merged["surgery"]
    hosp = merged["hospitalized"]
    if surgery.value is None or hosp.value is None:
        return None  # 둘 다 확인되기 전에는 모순 여부를 판단할 수 없음
    contradiction = surgery.value is True and hosp.value is False
    detail = (
        "수술을 받았다고 확인되었으나 입원 여부는 '아니오'로 되어 있어 모순 가능성이 있습니다. 재확인이 필요합니다."
        if contradiction else "수술·입원 여부 간 명백한 모순이 발견되지 않았습니다."
    )
    return {"rule_code": "CONTRADICTION_SURGERY_HOSP", "passed": not contradiction, "detail": detail}


def run_core_validation(db: Session, user_id: int, occurred_at, merged: dict[str, ExtractedField]) -> list[dict]:
    results = []
    for r in (
        check_period_mismatch(db, user_id, occurred_at),
        check_info_missing(merged),
        check_surgery_hospitalized_contradiction(merged),
    ):
        if r is not None:
            results.append(r)
    return results


def check_docs_not_secured(db: Session, incident_id: int) -> dict | None:
    """evidence 테이블에 기록된 필수서류 중 미보유/발급불가가 있는지 확인. (서류체크 이후에만 의미 있음)"""
    from app.models.user import Evidence

    records = db.query(Evidence).filter(Evidence.incident_id == incident_id).all()
    if not records:
        return None  # 아직 서류체크를 시작하지 않음 → 판단 보류
    not_secured = [e for e in records if e.status in ("미보유", "발급불가")]
    passed = len(not_secured) == 0
    if passed:
        detail = "기록된 서류 확보 현황상 미확보 서류가 없습니다."
    else:
        names = ", ".join(
            (e.required_doc_std.doc_name if e.required_doc_std else "미상")
            + ("(발급불가)" if e.status == "발급불가" else "(미보유)")
            for e in not_secured
        )
        detail = f"아직 확보되지 않은 서류가 있습니다: {names}"
    return {"rule_code": "DOC_NOT_SECURED", "passed": passed, "detail": detail}


def persist_validation(db: Session, run: AnalysisRun, results: list[dict]) -> list[ValidationResultOut]:
    out = []
    for r in results:
        rule = db.query(ValidationRule).filter_by(rule_code=r["rule_code"]).first()
        if not rule:
            continue  # 정의되지 않은 규칙 코드는 저장하지 않는다 (seed_validation_rules.py 참조)
        db.add(ValidationResult(
            analysis_run_id=run.analysis_run_id, rule_id=rule.rule_id,
            passed=r["passed"], detail=r["detail"],
        ))
        out.append(ValidationResultOut(
            rule_code=rule.rule_code, rule_name=rule.rule_name, severity=rule.severity,
            passed=r["passed"], detail=r["detail"],
        ))
    return out
