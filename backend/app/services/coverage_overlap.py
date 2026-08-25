"""기존보험과 이번 여행자보험 담보의 겹침·공백을 진단한다.

조회할 때마다 계산하고 저장하지 않는다 — 약관 DB가 갱신되면 결과도 자동으로 따라오고,
데이터가 작아(담보 수십 개) 성능 문제가 없다. 저장하면 약관이 바뀌었을 때 낡은 결과가 남는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.external import ExternalPolicy, OverlapRule
from app.models.kb import Clause, CoverageStd
from app.services.clause_quote import quote_clause


@dataclass
class OverlapFinding:
    coverage_std_id: int
    coverage_std_code: str
    coverage_std_name: str
    external_kind: str
    scope: str
    relation: str
    note: str | None = None
    clause_id: int | None = None
    clause_article_no: str | None = None
    #: 근거 조항 원문의 부분 문자열. 원문에 없는 글자는 절대 담지 않는다.
    clause_quote: str | None = None


@dataclass
class OverlapReport:
    duplicates: list[OverlapFinding] = field(default_factory=list)
    gaps: list[OverlapFinding] = field(default_factory=list)
    fixed_ok: list[OverlapFinding] = field(default_factory=list)
    unknown: list[OverlapFinding] = field(default_factory=list)


def diagnose(
    db: Session, *, external_policies: list[ExternalPolicy], target_coverage_std_ids: list[int]
) -> OverlapReport:
    """기존보험 목록과 검토할 담보 목록을 받아 진단 결과를 만든다.

    기존보험이 하나도 없으면 비교 대상이 없으므로 빈 보고서를 돌려준다.
    """
    report = OverlapReport()
    if not external_policies or not target_coverage_std_ids:
        return report

    kinds = {p.kind for p in external_policies}
    # 'ANY'는 "어떤 기존보험을 갖고 있든" 매칭되는 규칙용 센티널이다(예: 여권분실·항공기납치 —
    # 기존보험 종류와 무관하게 다른 계약과의 비례분담·중복 규정이 적용된다). 사용자가 실제로
    # 고른 종류만으로 필터하면 이런 규칙이 "그 외"를 명시적으로 고른 사람에게만 보이게 된다.
    lookup_kinds = kinds | {"ANY"}

    stds = {
        s.coverage_std_id: s
        for s in db.query(CoverageStd)
        .filter(CoverageStd.coverage_std_id.in_(target_coverage_std_ids))
        .all()
    }
    rules = (
        db.query(OverlapRule)
        .filter(OverlapRule.external_kind.in_(lookup_kinds))
        .filter(OverlapRule.coverage_std_id.in_(target_coverage_std_ids))
        .all()
    )
    clauses = {
        c.clause_id: c
        for c in db.query(Clause)
        .filter(Clause.clause_id.in_([r.clause_id for r in rules if r.clause_id]))
        .all()
    } if rules else {}

    matched_std_ids = set()
    for rule in rules:
        std = stds.get(rule.coverage_std_id)
        if std is None:
            continue
        matched_std_ids.add(rule.coverage_std_id)
        clause = clauses.get(rule.clause_id) if rule.clause_id else None
        finding = OverlapFinding(
            coverage_std_id=std.coverage_std_id,
            coverage_std_code=std.std_code,
            coverage_std_name=std.std_name,
            external_kind=rule.external_kind,
            scope=rule.scope,
            relation=rule.relation,
            note=rule.note,
            clause_id=rule.clause_id,
            clause_article_no=clause.article_no if clause else None,
            clause_quote=quote_clause(clause, rule.anchor_phrase),
        )
        if rule.relation in ("DUPLICATE_PRORATA", "PARTIAL"):
            report.duplicates.append(finding)
        elif rule.relation == "DUPLICATE_FIXED":
            report.fixed_ok.append(finding)
        elif rule.relation == "NO_OVERLAP":
            report.gaps.append(finding)
        else:
            report.unknown.append(finding)

    # 규칙이 없는 조합은 조용히 빠뜨리지 않고 "확인불가"로 남긴다 — 근거가 없다는 사실 자체가
    # 사용자에게 전달돼야 할 정보다.
    for std_id in target_coverage_std_ids:
        if std_id in matched_std_ids:
            continue
        std = stds.get(std_id)
        if std is None:
            continue
        report.unknown.append(OverlapFinding(
            coverage_std_id=std.coverage_std_id,
            coverage_std_code=std.std_code,
            coverage_std_name=std.std_name,
            external_kind=",".join(sorted(kinds)),
            scope="전체",
            relation="UNKNOWN",
            note="이 조합에 대한 약관 근거를 찾지 못했습니다.",
        ))

    return report
