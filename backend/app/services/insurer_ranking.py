"""약관 근거 기반 보험사 상대 비교 엔진.

이 모듈은 객관적 확률이나 전문가 평점을 만들지 않는다. 사용자가 선택한 사고유형과
직접 연결된 약관·정량조건·필요서류만 네 가지 비교축으로 집계하고, 보험사 사이의
상대적 우선순위만 결정한다.

평가축:
  - coverage_fit: 선택 사고유형에 직접/조건부로 연결된 보장 근거
  - condition_clarity: 관련 담보의 ClauseTerm 구조화 근거(완결성이 확인된 경우만 비교)
  - claim_simplicity: 관련 담보의 필수서류 근거(전수 검증된 경우에만 비교 가능)
  - restrictions: 선택 사고유형의 조건부/면책 근거(전수 검증된 경우에만 비교 가능)

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
# NOTE: kb_provenance.ranking_eligible_insurer_codes()는 아직 여기서 쓰지 않는다.
# 처음 이 주석을 달 때는 출처 검증이 끝난 곳이 6개사 중 3곳뿐이라 필터를 걸면 비교
# 대상이 절반으로 줄었다. 2026-08-18 재구축과 2026-08-25 신한 추가를 거치며 지금은
# 7개사 전부 VERIFIED_ISSUED_FILE(ranking_eligible=True)이라 걸어도 빠지는 곳이 없다.
# 그래도 켜지 않는 이유는 달라졌다 — 지금 켜면 아무 효과가 없고, 나중에 검증이 덜 끝난
# 보험사가 들어오는 순간 화면에서 조용히 사라지는 변화가 되기 때문이다. 그때는 빠진
# 사유를 함께 보여줄지(_drop_insurers_without_plan처럼) 먼저 정해야 한다.


_L1_CODES = {"INJ", "ILL", "PROP", "LIA", "TRV", "CHG", "EMG", "SPC"}
_DIMENSION_ORDER = ("coverage_fit", "condition_clarity", "claim_simplicity", "restrictions")
AVAILABLE = "AVAILABLE"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"
# 화면에 그대로 나가는 문구다. 비교 가능한 축은 단계가 높을수록 사용자에게 유리한
# 방향으로 읽히게 하고, 비교 불가 축은 level 대신 상태 문구를 쓴다.
_DIMENSION_LABELS = {
    "coverage_fit": "걱정한 사고를 챙겨줘요",
    "condition_clarity": "조건이 숫자로 또렷해요",
    "claim_simplicity": "청구가 간단해요",
    "restrictions": "막히는 조건이 적어요",
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
    comparison_state: str = AVAILABLE
    known_count: int = 0
    total_count: int = 0
    level: int = 0

    @property
    def available(self) -> bool:
        return self.comparison_state == AVAILABLE and self.value is not None

    def as_dict(self) -> dict:
        completeness_rate = (
            round(self.known_count / self.total_count * 100, 1)
            if self.total_count
            else None
        )
        return {
            "code": self.code,
            "label": _DIMENSION_LABELS[self.code],
            "level": self.level,
            "status": _dimension_status(self),
            "summary": self.summary,
            "evidence_count": len(self.evidence),
            "evidence": [item.as_dict() for item in self.evidence[:12]],
            "comparison_state": self.comparison_state,
            "available": self.available,
            "known_count": self.known_count,
            "total_count": self.total_count,
            "completeness_rate": completeness_rate,
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


def _dimension_status(metric: DimensionMetric) -> str:
    if metric.comparison_state == UNKNOWN:
        return "근거 부족"
    if metric.comparison_state == NOT_APPLICABLE:
        return "비교 제외"
    return _level_status(metric.level)


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

    mapped_l1_codes = {
        code
        for code, values in relevance_by_l1.items()
        if values & {"직접", "조건부", "면책"}
    }
    missing_l1_codes = l1_codes - mapped_l1_codes
    direct_count = sum("직접" in values for values in relevance_by_l1.values())
    conditional_only_count = sum(
        "직접" not in values and "조건부" in values for values in relevance_by_l1.values()
    )
    exclusion_only_count = sum(
        "면책" in values and not (values & {"직접", "조건부"})
        for values in relevance_by_l1.values()
    )
    fit_state = UNKNOWN if missing_l1_codes else AVAILABLE
    fit_value = (
        (direct_count + conditional_only_count * 0.5) / len(l1_codes)
        if fit_state == AVAILABLE
        else None
    )
    fit_summary = (
        f"선택 사고유형 {len(l1_codes)}개 중 직접 {direct_count}개, "
        f"조건부 {conditional_only_count}개, 명시적 면책 {exclusion_only_count}개, "
        f"미매핑 {len(missing_l1_codes)}개"
    )

    restricted_count = sum(
        bool(values & {"조건부", "면책"}) for values in relevance_by_l1.values()
    )
    restriction_summary = (
        f"조건부·면책 근거 {restricted_count}개 확인. 제한 없음에 대한 전수 검증 "
        "상태가 없어 보험사 간 비교에서 제외"
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
    if not supported_coverage_ids:
        clarity_state = NOT_APPLICABLE if fit_state == AVAILABLE else UNKNOWN
        clarity_value = None
    elif len(term_coverage_ids) == len(supported_coverage_ids):
        clarity_state = AVAILABLE
        clarity_value = 1.0
    else:
        # ClauseTerm은 양성 annotation만 저장한다. 따라서 누락은 실제 조건 불명확이
        # 아니라 데이터 미구축일 수 있으며, 부분 구축률을 제품 점수로 사용하지 않는다.
        clarity_state = UNKNOWN
        clarity_value = None
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
        f"관련 담보 {len(supported_coverage_ids)}개 중 구조화 조건 확인 "
        f"{len(term_coverage_ids)}개, 미검증 {len(supported_coverage_ids - term_coverage_ids)}개"
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
    # CoverageDocMap 역시 양성 annotation만 저장한다. 한 건 이상 있다는 사실은 알 수
    # 있지만 문서 목록이 완결됐다는 음성/완료 표시는 없으므로 개수를 성능점수로 쓰지 않는다.
    simplicity_value = None
    simplicity_state = (
        UNKNOWN
        if supported_coverage_ids
        else (NOT_APPLICABLE if fit_state == AVAILABLE else UNKNOWN)
    )
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
        f"관련 담보 {len(supported_coverage_ids)}개 중 서류 근거 확인 "
        f"{sum(bool(links) for links in docs_by_coverage.values())}개. "
        "전수 검증 상태가 없어 보험사 간 비교에서 제외"
        if supported_coverage_ids
        else "청구서류를 평가할 보장 담보가 없어 비교에서 제외"
    )

    dimensions = {
        "coverage_fit": DimensionMetric(
            code="coverage_fit", value=fit_value, summary=fit_summary,
            evidence=_dedupe_evidence(fit_evidence),
            comparison_state=fit_state,
            known_count=len(mapped_l1_codes), total_count=len(l1_codes),
        ),
        "condition_clarity": DimensionMetric(
            code="condition_clarity", value=clarity_value, summary=clarity_summary,
            evidence=clarity_evidence,
            comparison_state=clarity_state,
            known_count=len(term_coverage_ids), total_count=len(supported_coverage_ids),
        ),
        "claim_simplicity": DimensionMetric(
            code="claim_simplicity", value=simplicity_value, summary=simplicity_summary,
            evidence=doc_evidence,
            comparison_state=simplicity_state,
            known_count=sum(bool(links) for links in docs_by_coverage.values()),
            total_count=len(supported_coverage_ids),
        ),
        "restrictions": DimensionMetric(
            code="restrictions", value=None, summary=restriction_summary,
            evidence=_dedupe_evidence(restriction_evidence),
            comparison_state=UNKNOWN,
            known_count=restricted_count, total_count=len(l1_codes),
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
    """각 평가축을 보험사 사이의 상대 단계(1~5)로 변환한다."""
    for code in _DIMENSION_ORDER:
        values = sorted({
            evaluation.dimensions[code].value
            for evaluation in evaluations
            if evaluation.dimensions[code].available
        })
        if not values:
            continue
        for evaluation in evaluations:
            metric = evaluation.dimensions[code]
            if not metric.available:
                metric.level = 0
            elif len(values) == 1:
                metric.level = 3
            else:
                position = values.index(metric.value)
                metric.level = 1 + round(position / (len(values) - 1) * 4)


def _exclude_incomplete_comparison_cohorts(
    evaluations: list[InsurerEvaluation],
) -> None:
    """부분 annotation이 보험상품의 상대 우위로 바뀌지 않게 한다.

    ClauseTerm에는 '검토 완료 후 해당 조건 없음'을 표현하는 음성 레코드가 없다.
    한 보험사라도 UNKNOWN이면 완성돼 보이는 보험사를 더 높게 평가할 근거 역시
    부족하므로 condition_clarity 비교군 전체를 제외한다.
    """
    metrics = [evaluation.dimensions["condition_clarity"] for evaluation in evaluations]
    if not any(metric.comparison_state == UNKNOWN for metric in metrics):
        return
    for metric in metrics:
        if metric.comparison_state != AVAILABLE:
            continue
        metric.value = None
        metric.level = 0
        metric.comparison_state = UNKNOWN
        metric.summary += " (비교군 일부의 근거가 미구축되어 상대 비교 제외)"


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
    available_codes = [
        code for code in weights if evaluation.dimensions[code].available
    ]
    weight_sum = sum(weights[code] for code in available_codes)
    if weight_sum <= 0:
        return 0.0
    return sum(
        weights[code] / weight_sum * (evaluation.dimensions[code].level / 5)
        for code in available_codes
    )


def rank_insurers(db: Session, tier_code: str, trip_context: dict | None = None) -> list[dict]:
    """실제 DB 근거로 결정적인 상대 순위와 네 평가축을 반환한다."""
    if tier_code not in TIERS:
        raise ValueError(f"알 수 없는 랭킹 유형입니다: {tier_code}")

    l1_codes = _selected_l1_codes(trip_context)
    evaluations = [
        _collect_evaluation(db, insurer, l1_codes)
        for insurer in db.query(Insurer).order_by(Insurer.code).all()
    ]
    _exclude_incomplete_comparison_cohorts(evaluations)
    _assign_relative_levels(evaluations)
    weights = TIERS[tier_code]["weights"]
    evaluations.sort(
        key=lambda evaluation: (-_comparison_value(evaluation, weights), evaluation.insurer_code)
    )

    ranking: list[dict] = []
    for index, evaluation in enumerate(evaluations, start=1):
        dimensions = [evaluation.dimensions[code].as_dict() for code in _DIMENSION_ORDER]
        # 라벨이 이미 "~해요"로 끝나는 문장이라 등급을 뒤에 붙이면 말이 어색해진다.
        # 가장 잘하는 축만 부사로 세기를 구분해 강점 한 줄로 쓴다(단계 자체는 막대로 보여준다).
        tags = [
            f"{'특히 ' if dimension['level'] == 5 else ''}{dimension['label']}"
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
