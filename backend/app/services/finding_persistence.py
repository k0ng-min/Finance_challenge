"""
finding spec(dict) -> AnalysisFinding/FindingEvidenceLink DB 저장 + FindingOut 변환 공통 로직.
가입 전 추천(trips)과 사고 후 청구검토(incidents)가 동일한 규칙을 공유한다:
근거 clause가 없으면 반드시 status='확인불가' (new.md finding_evidence_link 규칙).
"""
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisFinding, FindingEvidenceLink, AnalysisRun
from app.schemas import FindingOut, ClauseOut


def persist_findings(db: Session, run: AnalysisRun, finding_specs: list[dict]) -> list[FindingOut]:
    findings_out: list[FindingOut] = []
    for spec in finding_specs:
        status = spec["status"] if spec["evidence"] else "확인불가"
        stored_target_ref = (
            f"[{spec['insurer_name']}] {spec['target_ref']}" if spec.get("insurer_name") else spec["target_ref"]
        )
        finding = AnalysisFinding(
            analysis_run_id=run.analysis_run_id,
            finding_type=spec["finding_type"],
            status=status,
            target_ref=stored_target_ref,
            description=spec["description"],
            confidence=spec["confidence"],
            coverage_amount=spec.get("coverage_amount"),
        )
        db.add(finding)
        db.flush()

        clause_outs = []
        for clause, color in spec["evidence"]:
            link = FindingEvidenceLink(
                finding_id=finding.finding_id,
                clause_id=clause.clause_id,
                highlight_color=color,
            )
            db.add(link)
            clause_outs.append(ClauseOut(
                clause_id=clause.clause_id,
                article_no=clause.article_no,
                text=clause.text,
                page_ref=clause.page_ref,
                default_color=clause.default_color,
                highlight_color=color,
            ))

        findings_out.append(FindingOut(
            finding_id=finding.finding_id,
            finding_type=finding.finding_type,
            status=finding.status,
            target_ref=finding.target_ref,
            insurer_code=spec.get("insurer_code"),
            insurer_name=spec.get("insurer_name"),
            description=finding.description,
            confidence=finding.confidence,
            coverage_amount=finding.coverage_amount,
            clauses=clause_outs,
        ))
    return findings_out


def load_findings_out(db: Session, analysis_run_id: int) -> list[FindingOut]:
    """이미 저장된 finding+근거링크를 다시 계산하지 않고 그대로 읽어 FindingOut으로 변환한다.
    (페이지 재방문 시 규칙엔진을 다시 돌리지 않기 위한 조회 전용 경로)"""
    findings = (
        db.query(AnalysisFinding)
        .filter(AnalysisFinding.analysis_run_id == analysis_run_id)
        .order_by(AnalysisFinding.finding_id)
        .all()
    )
    out = []
    for finding in findings:
        links = (
            db.query(FindingEvidenceLink)
            .filter(FindingEvidenceLink.finding_id == finding.finding_id)
            .all()
        )
        clause_outs = [
            ClauseOut(
                clause_id=link.clause.clause_id,
                article_no=link.clause.article_no,
                text=link.clause.text,
                page_ref=link.clause.page_ref,
                default_color=link.clause.default_color,
                highlight_color=link.highlight_color,
            )
            for link in links
        ]
        # target_ref에 저장 시 "[보험사명] " 접두어를 붙였다면 다시 분리해서 insurer_name으로 복원
        insurer_name = None
        target_ref = finding.target_ref
        if target_ref and target_ref.startswith("["):
            end = target_ref.find("]")
            if end != -1:
                insurer_name = target_ref[1:end]
                target_ref = target_ref[end + 2:] if len(target_ref) > end + 1 else target_ref
        out.append(FindingOut(
            finding_id=finding.finding_id,
            finding_type=finding.finding_type,
            status=finding.status,
            target_ref=target_ref,
            insurer_code=None,
            insurer_name=insurer_name,
            description=finding.description,
            confidence=finding.confidence,
            coverage_amount=finding.coverage_amount,
            clauses=clause_outs,
        ))
    return out
