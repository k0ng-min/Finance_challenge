"""약관 근거 기반 보험사 상대 비교 엔진.

이 모듈은 객관적 확률이나 전문가 평점을 만들지 않는다. 사용자가 선택한 사고유형과
직접 연결된 약관·정량조건·필요서류만 네 가지 비교축으로 집계하고, 보험사 사이의
상대적 우선순위만 결정한다.

평가축:
  - coverage_fit: 선택 사고유형에 직접/조건부로 연결된 보장 근거
  - condition_clarity: 관련 담보 중 ClauseTerm으로 조건이 구조화된 비율
  - claim_simplicity: 관련 담보의 필수서류 수(적을수록 우위)
  - restrictions: 선택 사고유형과 연결된 조건부/면책 범위(적을수록 우위)

전체 면책 조항 개수처럼 PDF 분할 방식에 좌우되는 값은 사용하지 않는다. 60~98점
정규화도 하지 않으며, 화면에는 1~5의 상대 단계와 근거 부족 상태만 노출한다.
동점이면 보험사 코드순으로 정렬해 언제나 같은 결과를 반환한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.kb import (
    Clause,
    ClauseIncidentMap,
    ClauseTerm,
    Coverage,
    CoverageDocMap,
    IncidentType,
    Insurer,
    PolicyVersion,
    Product,
)


_L1_CODES = {"INJ", "ILL", "PROP", "LIA", "TRV", "CHG", "EMG", "SPC"}
_DIMENSION_ORDER = ("coverage_fit", "condition_clarity", "claim_simplicity", "restrictions")
_DIMENSION_LABELS = {
    "coverage_fit": "관심사고 보장",
    "condition_clarity": "조건 명확성",
    "claim_simplicity": "청구 편의",
    "restrictions": "제한조건",
}


@dataclass(frozen=True)
class EvidenceRef:
    kind: str
    source_id: int
    coverage_name: str
    description: str
    page_ref: str | None = None

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "source_id": self.source_id,
            "coverage_name": self.coverage_name,
            "description": self.description,
            "page_ref": self.page_ref,
        }


@dataclass
class DimensionMetric:
    code: str
    value: float | None
    summary: str
    evidence: list[EvidenceRef] = field(default_factory=list)
    level: int = 0

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "label": _DIMENSION_LABELS[self.code],
            "level": self.level,
            "status": _level_status(self.level),
            "summary": self.summary,
            "evidence_count": len(self.evidence),
            "evidence": [item.as_dict() for item in self.evidence[:12]],
        }


@dataclass
class InsurerEvaluation:
    insurer_id: int
    insurer_code: str
    insurer_name: str
    official_url: str | None
    dimensions: dict[str, DimensionMetric]


def _selected_l1_codes(trip_context: dict | None) -> set[str]:
    selected = {
        value
        for value in ((trip_context or {}).get("coverage_priority") or [])
        if value in _L1_CODES
    }
    # 비교 기준을 고르기 전 API를 직접 호출해도 전체 KB를 근거로 결과를 낼 수 있게 한다.
    return selected or set(_L1_CODES)


def _level_status(level: int) -> str:
    return {
        0: "근거 부족",
        1: "상대적으로 낮음",
        2: "다소 낮음",
        3: "보통",
        4: "우수",
        5: "매우 우수",
    }[level]


def _dedupe_evidence(items: list[EvidenceRef]) -> list[EvidenceRef]:
    seen: set[tuple[str, int]] = set()
    result: list[EvidenceRef] = []
    for item in items:
        key = (item.kind, item.source_id)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _collect_evaluation(db: Session, insurer: Insurer, l1_codes: set[str]) -> InsurerEvaluation:
    rows = (
        db.query(ClauseIncidentMap, Clause, Coverage, IncidentType)
        .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
        .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Coverage.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(IncidentType, IncidentType.type_id == ClauseIncidentMap.type_id)
        .filter(Product.insurer_id == insurer.insurer_id, IncidentType.l1_code.in_(l1_codes))
        .all()
    )

    relevance_by_l1: dict[str, set[str]] = {code: set() for code in l1_codes}
    supported_coverage_ids: set[int] = set()
    fit_evidence: list[EvidenceRef] = []
    restriction_evidence: list[EvidenceRef] = []

    for mapping, clause, coverage, incident_type in rows:
        relevance_by_l1[incident_type.l1_code].add(mapping.relevance)
        evidence = EvidenceRef(
            kind="clause",
            source_id=clause.clause_id,
            coverage_name=coverage.raw_name,
            description=f"{incident_type.l1_code} · {mapping.relevance} · {clause.article_no or '조항'}",
            page_ref=clause.page_ref,
        )
        if mapping.relevance in {"직접", "조건부"}:
            supported_coverage_ids.add(coverage.coverage_id)
            fit_evidence.append(evidence)
        if mapping.relevance in {"조건부", "면책"}:
            restriction_evidence.append(evidence)

    direct_count = sum("직접" in values for values in relevance_by_l1.values())
    conditional_only_count = sum(
        "직접" not in values and "조건부" in values for values in relevance_by_l1.values()
    )
    unsupported_count = len(l1_codes) - direct_count - conditional_only_count
    fit_value = (direct_count + conditional_only_count * 0.5) / len(l1_codes) if rows else None
    fit_summary = (
        f"선택 사고유형 {len(l1_codes)}개 중 직접 {direct_count}개, "
        f"조건부 {conditional_only_count}개, 근거 미확인 {unsupported_count}개"
        if rows
        else "선택 사고유형과 연결된 약관 근거를 확인하지 못했습니다."
    )

    restricted_count = sum(
        bool(values & {"조건부", "면책"}) for values in relevance_by_l1.values()
    )
    restriction_value = 1 - (restricted_count / len(l1_codes)) if rows else None
    restriction_summary = (
        f"선택 사고유형 중 조건부·면책 근거가 연결된 유형 {restricted_count}개"
        if rows
        else "관련 제한조건을 평가할 약관 매핑이 없습니다."
    )

    term_rows: list[tuple[ClauseTerm, Clause, Coverage]] = []
    if supported_coverage_ids:
        term_rows = (
            db.query(ClauseTerm, Clause, Coverage)
            .join(Clause, Clause.clause_id == ClauseTerm.clause_id)
            .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
            .filter(Coverage.coverage_id.in_(supported_coverage_ids))
            .all()
        )
    term_coverage_ids = {coverage.coverage_id for _, _, coverage in term_rows}
    clarity_value = (
        len(term_coverage_ids) / len(supported_coverage_ids) if supported_coverage_ids else None
    )
    clarity_evidence = _dedupe_evidence([
        EvidenceRef(
            kind="term",
            source_id=term.term_id,
            coverage_name=coverage.raw_name,
            description=f"{term.term_type} · {term.raw_text}",
            page_ref=clause.page_ref,
        )
        for term, clause, coverage in term_rows
    ])
    clarity_summary = (
        f"관련 담보 {len(supported_coverage_ids)}개 중 {len(term_coverage_ids)}개에 "
        "지급한도·자기부담금 등 구조화 조건이 있습니다."
        if supported_coverage_ids
        else "조건 명확성을 평가할 보장 근거가 없습니다."
    )

    doc_rows: list[tuple[CoverageDocMap, Coverage]] = []
    if supported_coverage_ids:
        doc_rows = (
            db.query(CoverageDocMap, Coverage)
            .join(Coverage, Coverage.coverage_id == CoverageDocMap.coverage_id)
            .filter(CoverageDocMap.coverage_id.in_(supported_coverage_ids))
            .all()
        )
    docs_by_coverage: dict[int, list[CoverageDocMap]] = {
        coverage_id: [] for coverage_id in supported_coverage_ids
    }
    for doc_map, coverage in doc_rows:
        docs_by_coverage[coverage.coverage_id].append(doc_map)
    docs_complete = bool(supported_coverage_ids) and all(docs_by_coverage.values())
    mandatory_counts = [
        sum(link.is_mandatory for link in links) for links in docs_by_coverage.values()
    ]
    average_mandatory = (
        sum(mandatory_counts) / len(mandatory_counts) if docs_complete else None
    )
    # 상대 단계 산정에는 필수서류 평균의 부호만 뒤집어 사용한다. 절대 점수로 해석하지 않는다.
    simplicity_value = -average_mandatory if average_mandatory is not None else None
    doc_evidence = _dedupe_evidence([
        EvidenceRef(
            kind="document",
            source_id=doc_map.coverage_doc_id,
            coverage_name=coverage.raw_name,
            description=(
                f"{'필수' if doc_map.is_mandatory else '조건부'} · "
                f"{doc_map.required_doc_std.doc_name}"
            ),
            page_ref=doc_map.clause.page_ref if doc_map.clause else None,
        )
        for doc_map, coverage in doc_rows
    ])
    simplicity_summary = (
        f"관련 담보당 필수서류가 평균 {average_mandatory:.1f}종입니다."
        if average_mandatory is not None
        else "관련 담보 전체의 필요서류 근거가 갖춰지지 않아 비교에서 보수적으로 처리합니다."
    )

    dimensions = {
        "coverage_fit": DimensionMetric(
            code="coverage_fit", value=fit_value, summary=fit_summary,
            evidence=_dedupe_evidence(fit_evidence),
        ),
        "condition_clarity": DimensionMetric(
            code="condition_clarity", value=clarity_value, summary=clarity_summary,
            evidence=clarity_evidence,
        ),
        "claim_simplicity": DimensionMetric(
            code="claim_simplicity", value=simplicity_value, summary=simplicity_summary,
            evidence=doc_evidence,
        ),
        "restrictions": DimensionMetric(
            code="restrictions", value=restriction_value, summary=restriction_summary,
            evidence=_dedupe_evidence(restriction_evidence),
        ),
    }
    return InsurerEvaluation(
        insurer_id=insurer.insurer_id,
        insurer_code=insurer.code,
        insurer_name=insurer.name,
        official_url=insurer.official_url,
        dimensions=dimensions,
    )


def _assign_relative_levels(evaluations: list[InsurerEvaluation]) -> None:
    """각 평가축을 보험사 사이의 상대 단계(1~5)로 변환한다. 근거가 없으면 0이다."""
    for code in _DIMENSION_ORDER:
        values = sorted({
            evaluation.dimensions[code].value
            for evaluation in evaluations
            if evaluation.dimensions[code].value is not None
        })
        if not values:
            continue
        for evaluation in evaluations:
            metric = evaluation.dimensions[code]
            if metric.value is None:
                metric.level = 0
            elif len(values) == 1:
                metric.level = 3
            else:
                position = values.index(metric.value)
                metric.level = 1 + round(position / (len(values) - 1) * 4)


TIERS = {
    "안정형": {
        "label": "안정형",
        "description": "관심사고 보장과 관련 제한조건을 우선해 비교합니다.",
        "weights": {"coverage_fit": 0.40, "restrictions": 0.35, "condition_clarity": 0.15, "claim_simplicity": 0.10},
    },
    "실속형": {
        "label": "실속형",
        "description": "보장 근거와 조건 명확성, 청구 편의를 고르게 비교합니다.",
        "weights": {"coverage_fit": 0.35, "condition_clarity": 0.25, "restrictions": 0.20, "claim_simplicity": 0.20},
    },
    "최대보장형": {
        "label": "최대보장형",
        "description": "관심사고와 직접 연결된 보장 근거를 가장 크게 반영합니다.",
        "weights": {"coverage_fit": 0.50, "condition_clarity": 0.30, "restrictions": 0.15, "claim_simplicity": 0.05},
    },
    "간편청구형": {
        "label": "간편청구형",
        "description": "관련 담보의 필수서류 수와 조건 명확성을 우선해 비교합니다.",
        "weights": {"claim_simplicity": 0.40, "coverage_fit": 0.30, "condition_clarity": 0.20, "restrictions": 0.10},
    },
    "균형형": {
        "label": "균형형",
        "description": "네 가지 근거 축을 균형 있게 반영한 상대 비교입니다.",
        "weights": {"coverage_fit": 0.35, "condition_clarity": 0.25, "restrictions": 0.20, "claim_simplicity": 0.20},
    },
}


def list_tiers() -> list[dict]:
    return [
        {"tier_code": code, "label": config["label"], "description": config["description"]}
        for code, config in TIERS.items()
    ]


def _comparison_value(evaluation: InsurerEvaluation, weights: dict[str, float]) -> float:
    # 근거 부족(level=0)은 유리한 것으로 오인하지 않도록 0으로 보수 처리한다.
    return sum(weights[code] * (evaluation.dimensions[code].level / 5) for code in weights)


def rank_insurers(db: Session, tier_code: str, trip_context: dict | None = None) -> list[dict]:
    """실제 DB 근거로 결정적인 상대 순위와 네 평가축을 반환한다."""
    if tier_code not in TIERS:
        raise ValueError(f"알 수 없는 랭킹 유형입니다: {tier_code}")

    l1_codes = _selected_l1_codes(trip_context)
    evaluations = [
        _collect_evaluation(db, insurer, l1_codes)
        for insurer in db.query(Insurer).order_by(Insurer.code).all()
    ]
    _assign_relative_levels(evaluations)
    weights = TIERS[tier_code]["weights"]
    evaluations.sort(
        key=lambda evaluation: (-_comparison_value(evaluation, weights), evaluation.insurer_code)
    )

    ranking: list[dict] = []
    for index, evaluation in enumerate(evaluations, start=1):
        dimensions = [evaluation.dimensions[code].as_dict() for code in _DIMENSION_ORDER]
        tags = [
            f"{dimension['label']} {dimension['status']}"
            for dimension in dimensions
            if dimension["level"] >= 4
        ]
        ranking.append({
            "rank": index,
            "insurer_code": evaluation.insurer_code,
            "insurer_name": evaluation.insurer_name,
            "comparison_basis": f"{tier_code} 기준 상대 비교",
            "dimensions": dimensions,
            "reasons": [dimension["summary"] for dimension in dimensions],
            "tags": tags,
            "official_url": evaluation.official_url,
        })
    return ranking
