"""실제 KB에 연결된 청구지원 End-to-End golden set 평가.

기존 ``evaluate_incident_classifier.py``를 대체하지 않는다. 그 평가가 저장한 원시
L1/L2 예측을 재사용하고, 같은 사고가 실제 청구지원 경로를 통과했을 때 담보·약관·서류·
직접/조건부/면책 관계와 unsupported 처리가 어떻게 이어지는지를 별도로 측정한다.

golden set의 downstream 정답은 모델 출력이 아니라 app.db의 Coverage,
ClauseIncidentMap, CoverageDocMap으로 검증한다. 평가용 사용자/가입담보는 세션에 flush만
하고 매 사례 rollback하므로 운영 데이터에는 남지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageDocMap, IncidentType,
)
from app.models.user import AppUser, Incident, UserCoverage, UserPolicy
from app.services import claim_review, incident_classify_gemini as classifier, nlu
from app.services.clause_quote import quote_clause
from eval.evaluate_incident_classifier import collect_live_predictions, macro_f1, prompt_sha256

EVALUATION_VERSION = "claim-pipeline-eval-v1"
DIFFICULTIES = ("easy", "hard", "ambiguous")
RELATIONS = {"직접", "조건부", "면책"}
DECISIVE_FINDING_TYPES = {"추천담보", "제한조건"}
UNKNOWN_STATUSES = {"확인불가", "근거 부족", "비교 제외"}


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _round(value: float) -> float:
    return round(value, 4)


def dataset_sha256(rows: list[dict]) -> str:
    canonical = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: JSON 형식 오류: {exc}") from exc
    return rows


def load_prediction_payload(path: Path) -> tuple[list[dict], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload, {}
    predictions = payload.get("predictions")
    if not isinstance(predictions, list):
        raise ValueError(f"{path}: predictions 배열이 없습니다")
    metadata = {
        key: payload.get(key)
        for key in ("evaluation_version", "model", "prompt_sha256", "dataset_sha256")
        if payload.get(key) is not None
    }
    return predictions, metadata


def _coverage_for_selector(db: Session, selector: dict) -> Coverage:
    coverage_id = selector.get("coverage_id")
    coverage = db.get(Coverage, coverage_id) if isinstance(coverage_id, int) else None
    if coverage is None:
        raise ValueError(f"coverage_id={coverage_id!r}가 KB에 없습니다")
    insurer = coverage.policy_version.product.insurer
    std = coverage.coverage_std
    if insurer.code != selector.get("insurer_code"):
        raise ValueError(
            f"coverage_id={coverage_id}: insurer {insurer.code} != {selector.get('insurer_code')}"
        )
    if std is None or std.std_code != selector.get("coverage_std_code"):
        raise ValueError(
            f"coverage_id={coverage_id}: std_code {std.std_code if std else None} "
            f"!= {selector.get('coverage_std_code')}"
        )
    return coverage


def _type_by_l2(db: Session, l2_code: str) -> IncidentType | None:
    return db.query(IncidentType).filter(IncidentType.l2_code == l2_code).first()


def _type_by_l1(db: Session, l1_code: str) -> IncidentType | None:
    return (
        db.query(IncidentType)
        .filter(IncidentType.l1_code == l1_code, IncidentType.parent_id.is_(None))
        .first()
    )


def _kb_projection(
    db: Session, coverages: Iterable[Coverage], type_row: IncidentType,
    modifiers: dict | None = None,
) -> dict:
    coverage_codes: set[str] = set()
    mandatory_docs: set[str] = set()
    relations: set[tuple[str, str]] = set()
    clause_ids: set[int] = set()
    for coverage in coverages:
        maps = (
            db.query(ClauseIncidentMap)
            .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
            .filter(
                Clause.coverage_id == coverage.coverage_id,
                ClauseIncidentMap.type_id == type_row.type_id,
            )
            .all()
        )
        if not maps:
            continue
        std_code = coverage.coverage_std.std_code
        best = claim_review.rank_maps(maps, modifiers or {})[0]
        coverage_codes.add(std_code)
        relations.add((std_code, best.relevance))
        clause_ids.update(item.clause_id for item in maps)
        for doc_map in db.query(CoverageDocMap).filter_by(coverage_id=coverage.coverage_id):
            if doc_map.is_mandatory:
                mandatory_docs.add(doc_map.required_doc_std.doc_code)
    return {
        "coverage_std_codes": coverage_codes,
        "mandatory_doc_codes": mandatory_docs,
        "relations": relations,
        "clause_ids": clause_ids,
    }


def validate_dataset(
    rows: list[dict], db: Session, classifier_gold_rows: list[dict] | None = None,
) -> dict:
    """구조뿐 아니라 모든 downstream gold가 현재 KB에 실제로 존재하는지 검증한다."""
    if not 30 <= len(rows) <= 50:
        raise ValueError(f"claim pipeline gold는 30~50건이어야 합니다: {len(rows)}건")
    ids = [row.get("id") for row in rows]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("golden set id가 비었거나 중복되었습니다")

    source_by_id = {row["id"]: row for row in (classifier_gold_rows or [])}
    l1_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    unsupported_count = 0
    coverage_refs = 0
    clause_refs: set[int] = set()

    for row in rows:
        row_id = row["id"]
        if row.get("synthetic") is not True:
            raise ValueError(f"{row_id}: synthetic=true가 명시되어야 합니다")
        difficulty = row.get("difficulty")
        if difficulty not in DIFFICULTIES:
            raise ValueError(f"{row_id}: 잘못된 difficulty={difficulty!r}")
        l1 = row.get("expected_l1")
        if _type_by_l1(db, l1) is None:
            raise ValueError(f"{row_id}: KB에 없는 expected_l1={l1!r}")
        l1_counts[l1] += 1
        difficulty_counts[difficulty] += 1

        source_id = row.get("source_incident_gold_id")
        if source_by_id:
            source = source_by_id.get(source_id)
            if source is None:
                raise ValueError(f"{row_id}: 기존 사고분류 gold에 {source_id!r}가 없습니다")
            if source.get("text") != row.get("incident_text"):
                raise ValueError(f"{row_id}: 기존 사고분류 gold 문구가 변경됐습니다")
            if source.get("gold_l1") != l1 or source.get("gold_l2") != row.get("expected_l2"):
                raise ValueError(f"{row_id}: 기존 검수 L1/L2 라벨과 다릅니다")

        coverages = [_coverage_for_selector(db, item) for item in row.get("insured_coverages", [])]
        if not coverages:
            raise ValueError(f"{row_id}: insured_coverages가 비었습니다")
        coverage_refs += len(coverages)
        insured_codes = {coverage.coverage_std.std_code for coverage in coverages}
        expected_codes = set(row.get("expected_coverage_std_codes") or [])
        forbidden = set(row.get("must_not_include_coverage_std_codes") or [])
        if not expected_codes <= insured_codes or not forbidden <= insured_codes:
            raise ValueError(f"{row_id}: expected/must_not coverage는 가입담보 안에 있어야 합니다")
        if expected_codes & forbidden:
            raise ValueError(f"{row_id}: 같은 담보가 expected와 must_not에 함께 있습니다")

        expected_relations = {
            (item.get("coverage_std_code"), item.get("relation"))
            for item in row.get("expected_relations") or []
        }
        if any(relation not in RELATIONS for _, relation in expected_relations):
            raise ValueError(f"{row_id}: 직접/조건부/면책 외 relation이 있습니다")

        expected_l2 = row.get("expected_l2")
        expected_l2_abstain = bool(row.get("expected_l2_abstain", False))
        if expected_l2_abstain:
            if expected_l2 is not None:
                raise ValueError(f"{row_id}: L2 abstain 사례는 expected_l2가 null이어야 합니다")
            if expected_codes or row.get("expected_required_doc_codes") or expected_relations:
                raise ValueError(f"{row_id}: ambiguous 사례에 단일 downstream 정답을 강제할 수 없습니다")
        else:
            type_row = _type_by_l2(db, expected_l2)
            if type_row is None or type_row.l1_code != l1:
                raise ValueError(f"{row_id}: KB에 없는/잘못된 expected_l2={expected_l2!r}")
            projection = _kb_projection(db, coverages, type_row, row.get("modifiers"))
            if expected_codes != projection["coverage_std_codes"]:
                raise ValueError(
                    f"{row_id}: coverage gold가 KB와 다릅니다: "
                    f"gold={sorted(expected_codes)}, kb={sorted(projection['coverage_std_codes'])}"
                )
            expected_docs = set(row.get("expected_required_doc_codes") or [])
            if expected_docs != projection["mandatory_doc_codes"]:
                raise ValueError(
                    f"{row_id}: mandatory doc gold가 KB와 다릅니다: "
                    f"gold={sorted(expected_docs)}, kb={sorted(projection['mandatory_doc_codes'])}"
                )
            if expected_relations != projection["relations"]:
                raise ValueError(
                    f"{row_id}: relation gold가 KB와 다릅니다: "
                    f"gold={sorted(expected_relations)}, kb={sorted(projection['relations'])}"
                )
            clause_refs.update(projection["clause_ids"])
            if bool(row.get("expected_unsupported")) != (not expected_codes):
                raise ValueError(f"{row_id}: expected_unsupported가 KB mapping 유무와 다릅니다")

        if row.get("expected_unsupported"):
            unsupported_count += 1

    missing_l1 = sorted(set(classifier.L1_DESCRIPTIONS) - set(l1_counts))
    if missing_l1:
        raise ValueError(f"golden set에 없는 L1: {', '.join(missing_l1)}")
    missing_difficulty = sorted(set(DIFFICULTIES) - set(difficulty_counts))
    if missing_difficulty:
        raise ValueError(f"golden set에 없는 difficulty: {', '.join(missing_difficulty)}")
    return {
        "sample_count": len(rows),
        "synthetic": True,
        "l1_counts": dict(sorted(l1_counts.items())),
        "difficulty_counts": dict(sorted(difficulty_counts.items())),
        "expected_unsupported_count": unsupported_count,
        "insured_coverage_reference_count": coverage_refs,
        "grounded_gold_clause_count": len(clause_refs),
    }


def _final_classification(
    prediction: dict, *, incident_text: str, l1_threshold: float, l2_threshold: float,
) -> tuple[str | None, str | None]:
    override = classifier.deterministic_route_override(incident_text)
    if override is not None:
        return override[0], override[1]
    l1 = prediction.get("predicted_l1")
    if not l1 or float(prediction.get("l1_confidence") or 0.0) < l1_threshold:
        return None, None
    l2 = prediction.get("predicted_l2")
    if not l2 or float(prediction.get("l2_confidence") or 0.0) < l2_threshold:
        return l1, None
    if not str(l2).startswith(f"{l1}_"):
        return l1, None
    return l1, l2


def _scenario_prediction_from_gold(row: dict) -> dict:
    return {
        "id": row["id"],
        "predicted_l1": row["expected_l1"],
        "l1_confidence": 1.0,
        "predicted_l2": row.get("expected_l2"),
        "l2_confidence": 1.0 if row.get("expected_l2") else 0.0,
        "source": "gold-routing-oracle",
    }


def _run_claim_pipeline(
    db: Session, row: dict, prediction: dict, *, l1_threshold: float, l2_threshold: float,
) -> dict:
    predicted_l1, predicted_l2 = _final_classification(
        prediction, incident_text=row["incident_text"],
        l1_threshold=l1_threshold, l2_threshold=l2_threshold,
    )
    route_type = _type_by_l2(db, predicted_l2) if predicted_l2 else _type_by_l1(db, predicted_l1)
    if predicted_l2 and (route_type is None or route_type.l1_code != predicted_l1):
        route_type = _type_by_l1(db, predicted_l1)
        predicted_l2 = None

    original_enabled = config.GEMINI_ENABLED
    original_engine = nlu._engine_singleton
    try:
        # downstream 설명용 LLM은 평가 대상이 아니다. 담보/서류 선택은 같은 결정적 경로를
        # 쓰되 문장 장식용 외부 호출은 막아 평가를 재현 가능하게 한다.
        config.GEMINI_ENABLED = False
        nlu._engine_singleton = nlu.RuleBasedNLU()

        user = AppUser(nickname=f"claim-eval-{row['id']}")
        db.add(user)
        db.flush()
        policy_by_version: dict[int, UserPolicy] = {}
        for selector in row["insured_coverages"]:
            coverage = _coverage_for_selector(db, selector)
            policy = policy_by_version.get(coverage.policy_version_id)
            if policy is None:
                insurer = coverage.policy_version.product.insurer
                policy = UserPolicy(
                    user_id=user.user_id,
                    product_id=coverage.policy_version.product_id,
                    policy_version_id=coverage.policy_version_id,
                    insurer_name_raw=insurer.name,
                    product_name_raw=coverage.policy_version.product.name,
                )
                db.add(policy)
                db.flush()
                policy_by_version[coverage.policy_version_id] = policy
            db.add(UserCoverage(
                user_policy_id=policy.user_policy_id,
                coverage_id=coverage.coverage_id,
                coverage_std_id=coverage.coverage_std_id,
                raw_name=coverage.raw_name,
            ))

        incident = Incident(
            user_id=user.user_id,
            type_id=route_type.type_id if route_type else None,
            free_text=row["incident_text"],
            item_damage_type=row.get("item_damage_type"),
            modifiers=json.dumps(row.get("modifiers") or {}, ensure_ascii=False),
        )
        db.add(incident)
        db.flush()

        merged = {}
        finding_specs = claim_review.generate_claim_findings(db, incident, merged)
        routed_type_ids = claim_review.resolve_type_ids(db, incident.type_id, merged)
        relevant = list(claim_review.iter_relevant_user_coverages(
            db, user.user_id, incident.type_id, merged,
        ))

        coverage_codes: set[str] = set()
        mandatory_docs: set[str] = set()
        relations: set[tuple[str, str]] = set()
        clause_ids: set[int] = set()
        seen_coverages: set[int] = set()
        for _uc, coverage, _insurer in relevant:
            if coverage.coverage_id in seen_coverages:
                continue
            seen_coverages.add(coverage.coverage_id)
            matching_maps = []
            for type_id in routed_type_ids:
                maps = (
                    db.query(ClauseIncidentMap)
                    .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
                    .filter(
                        Clause.coverage_id == coverage.coverage_id,
                        ClauseIncidentMap.type_id == type_id,
                    )
                    .all()
                )
                if maps:
                    matching_maps = maps
                    break
            if not matching_maps:
                continue
            std_code = coverage.coverage_std.std_code
            best = claim_review.rank_maps(matching_maps, row.get("modifiers") or {})[0]
            coverage_codes.add(std_code)
            relations.add((std_code, best.relevance))
            clause_ids.update(item.clause_id for item in matching_maps)
            for doc_map in db.query(CoverageDocMap).filter_by(coverage_id=coverage.coverage_id):
                if doc_map.is_mandatory:
                    mandatory_docs.add(doc_map.required_doc_std.doc_code)

        citations = []
        decisive_count = 0
        unsupported_recommendations = 0
        for finding in finding_specs:
            evidence = finding.get("evidence") or []
            if finding.get("finding_type") in DECISIVE_FINDING_TYPES:
                decisive_count += 1
                evidence_ids = {clause.clause_id for clause, _color in evidence}
                if not evidence_ids or not evidence_ids <= clause_ids:
                    unsupported_recommendations += 1
            for clause, _color in evidence:
                citation = quote_clause(clause)
                grounded = bool(citation and citation in (clause.text or ""))
                citations.append({
                    "clause_id": clause.clause_id,
                    "citation": citation,
                    "grounded": grounded,
                })

        explicit_unsupported = any(
            finding.get("status") in UNKNOWN_STATUSES or finding.get("finding_type") == "보장공백"
            for finding in finding_specs
        )
        return {
            "id": row["id"],
            "difficulty": row["difficulty"],
            "predicted_l1": predicted_l1,
            "predicted_l2": predicted_l2,
            "coverage_std_codes": sorted(coverage_codes),
            "mandatory_doc_codes": sorted(mandatory_docs),
            "relations": [
                {"coverage_std_code": code, "relation": relation}
                for code, relation in sorted(relations)
            ],
            "clause_ids": sorted(clause_ids),
            "citations": citations,
            "decisive_recommendation_count": decisive_count,
            "unsupported_recommendation_count": unsupported_recommendations,
            "unsupported_result": not coverage_codes,
            "explicit_unsupported_result": explicit_unsupported,
            "finding_count": len(finding_specs),
        }
    finally:
        db.rollback()
        config.GEMINI_ENABLED = original_enabled
        nlu._engine_singleton = original_engine


def _set_counts(outcomes: list[dict], expected_key: str, actual_key: str) -> dict:
    tp = fp = fn = 0
    for outcome in outcomes:
        expected = set(outcome["gold"].get(expected_key) or [])
        actual = set(outcome["actual"].get(actual_key) or [])
        tp += len(expected & actual)
        fp += len(actual - expected)
        fn += len(expected - actual)
    return {
        "precision": _round(_safe_div(tp, tp + fp)),
        "recall": _round(_safe_div(tp, tp + fn)),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
    }


def _score_outcome(row: dict, actual: dict) -> dict:
    expected_l1 = {row["expected_l1"], *(row.get("acceptable_l1_codes") or [])}
    expected_l2 = {row.get("expected_l2"), *(row.get("acceptable_l2_codes") or [])} - {None}
    l1_ok = actual["predicted_l1"] in expected_l1
    l2_ok = (
        actual["predicted_l2"] is None
        if row.get("expected_l2_abstain")
        else actual["predicted_l2"] in expected_l2
    )
    expected_coverages = set(row.get("expected_coverage_std_codes") or [])
    actual_coverages = set(actual["coverage_std_codes"])
    forbidden = set(row.get("must_not_include_coverage_std_codes") or [])
    expected_docs = set(row.get("expected_required_doc_codes") or [])
    actual_docs = set(actual["mandatory_doc_codes"])
    expected_relations = {
        (item["coverage_std_code"], item["relation"])
        for item in row.get("expected_relations") or []
    }
    actual_relations = {
        (item["coverage_std_code"], item["relation"])
        for item in actual["relations"]
    }
    citations_grounded = all(item["grounded"] for item in actual["citations"])
    unsupported_ok = actual["unsupported_recommendation_count"] == 0
    unsupported_result_ok = actual["unsupported_result"] == bool(row.get("expected_unsupported"))
    explicit_unsupported_ok = (
        not row.get("expected_unsupported") or actual["explicit_unsupported_result"]
    )

    acceptable = all((
        l1_ok,
        l2_ok,
        expected_coverages <= actual_coverages,
        not (forbidden & actual_coverages),
        expected_docs <= actual_docs,
        expected_relations <= actual_relations,
        citations_grounded,
        unsupported_ok,
        unsupported_result_ok,
        explicit_unsupported_ok,
    ))
    exact = acceptable and all((
        actual_coverages == expected_coverages,
        actual_docs == expected_docs,
        actual_relations == expected_relations,
    ))

    errors = []
    if not l1_ok:
        errors.append("l1_mismatch")
    if not l2_ok:
        errors.append("l2_mismatch_or_abstention")
    if expected_coverages - actual_coverages:
        errors.append("coverage_missing")
    if actual_coverages - expected_coverages:
        errors.append("coverage_extra")
    if forbidden & actual_coverages:
        errors.append("forbidden_coverage")
    if expected_docs - actual_docs:
        errors.append("mandatory_document_missing")
    if actual_docs - expected_docs:
        errors.append("mandatory_document_extra")
    if expected_relations != actual_relations:
        errors.append("relation_mismatch")
    if not citations_grounded:
        errors.append("citation_not_grounded")
    if not unsupported_ok:
        errors.append("unsupported_recommendation")
    if not unsupported_result_ok:
        errors.append("unsupported_result_mismatch")
    if not explicit_unsupported_ok:
        errors.append("unsupported_result_not_explicit")
    return {"exact": exact, "acceptable": acceptable, "errors": errors}


def _aggregate(outcomes: list[dict]) -> dict:
    if not outcomes:
        return {"sample_count": 0}
    l1_true = [item["gold"]["expected_l1"] for item in outcomes]
    l1_pred = [item["actual"]["predicted_l1"] for item in outcomes]
    l1_labels = sorted(set(l1_true))
    l2_rows = [item for item in outcomes if not item["gold"].get("expected_l2_abstain")]
    l2_true = [item["gold"]["expected_l2"] for item in l2_rows]
    l2_pred = [item["actual"]["predicted_l2"] for item in l2_rows]
    l2_labels = sorted(set(l2_true))
    l2_abstain_rows = [item for item in outcomes if item["gold"].get("expected_l2_abstain")]
    citations = [citation for item in outcomes for citation in item["actual"]["citations"]]
    decisive = sum(item["actual"]["decisive_recommendation_count"] for item in outcomes)
    unsupported = sum(item["actual"]["unsupported_recommendation_count"] for item in outcomes)
    error_counts = Counter(error for item in outcomes for error in item["evaluation"]["errors"])
    return {
        "sample_count": len(outcomes),
        "l1_macro_f1": macro_f1(l1_true, l1_pred, l1_labels),
        "l2_end_to_end_macro_f1": macro_f1(l2_true, l2_pred, l2_labels) if l2_rows else None,
        "l2_evaluated_count": len(l2_rows),
        "l2_abstention_accuracy": _round(_safe_div(sum(
            item["actual"]["predicted_l2"] is None for item in l2_abstain_rows
        ), len(l2_abstain_rows))) if l2_abstain_rows else None,
        "coverage": _set_counts(outcomes, "expected_coverage_std_codes", "coverage_std_codes"),
        "mandatory_document": _set_counts(
            outcomes, "expected_required_doc_codes", "mandatory_doc_codes",
        ),
        "citation_grounding_rate": _round(_safe_div(
            sum(item["grounded"] for item in citations), len(citations),
        )),
        "citation_count": len(citations),
        "unsupported_recommendation_rate": _round(_safe_div(unsupported, decisive)),
        "unsupported_recommendation_count": unsupported,
        "decisive_recommendation_count": decisive,
        "unsupported_result_accuracy": _round(_safe_div(sum(
            item["actual"]["unsupported_result"] == bool(item["gold"].get("expected_unsupported"))
            for item in outcomes
        ), len(outcomes))),
        "explicit_unsupported_rate_when_expected": _round(_safe_div(sum(
            item["actual"]["explicit_unsupported_result"]
            for item in outcomes if item["gold"].get("expected_unsupported")
        ), sum(bool(item["gold"].get("expected_unsupported")) for item in outcomes))),
        "end_to_end_exact_success_rate": _round(_safe_div(sum(
            item["evaluation"]["exact"] for item in outcomes
        ), len(outcomes))),
        "end_to_end_acceptable_success_rate": _round(_safe_div(sum(
            item["evaluation"]["acceptable"] for item in outcomes
        ), len(outcomes))),
        "error_type_counts": dict(sorted(error_counts.items())),
    }


def build_report(
    rows: list[dict], predictions: list[dict], db: Session, *,
    l1_threshold: float = classifier.DEFAULT_L1_AUTO_THRESHOLD,
    l2_threshold: float = classifier.DEFAULT_L2_AUTO_THRESHOLD,
    prediction_metadata: dict | None = None,
    routing_mode: str = "cached-classifier-predictions",
) -> dict:
    by_id = {item.get("id"): item for item in predictions}
    if len(by_id) != len(predictions):
        raise ValueError("classifier prediction id가 중복되었습니다")
    missing = [row["id"] for row in rows if row["id"] not in by_id]
    if missing:
        raise ValueError(f"classifier prediction이 없는 scenario: {', '.join(missing[:5])}")

    outcomes = []
    for row in rows:
        actual = _run_claim_pipeline(
            db, row, by_id[row["id"]],
            l1_threshold=l1_threshold, l2_threshold=l2_threshold,
        )
        evaluation = _score_outcome(row, actual)
        outcomes.append({"id": row["id"], "gold": row, "actual": actual, "evaluation": evaluation})

    failures = [item for item in outcomes if not item["evaluation"]["acceptable"]]
    metadata = dict(prediction_metadata or {})
    current_prompt_hash = prompt_sha256()
    source_prompt_hash = metadata.get("prompt_sha256")
    metadata["current_prompt_sha256"] = current_prompt_hash
    metadata["matches_current_prompt"] = (
        source_prompt_hash == current_prompt_hash if source_prompt_hash else None
    )
    metadata["current_deterministic_route_overrides_applied"] = True
    return {
        "evaluation_version": EVALUATION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": dataset_sha256(rows),
        "routing_mode": routing_mode,
        "classifier_prediction_metadata": metadata,
        "thresholds": {"l1": l1_threshold, "l2": l2_threshold},
        "dataset": {
            "sample_count": len(rows),
            "synthetic": True,
            "note": (
                "검수용 synthetic 사고이며 L1/L2는 기존 classifier gold에서 가져오고, "
                "downstream 정답은 현재 KB mapping으로 교차검증했다."
            ),
        },
        "metrics": _aggregate(outcomes),
        "metrics_by_difficulty": {
            difficulty: _aggregate([
                item for item in outcomes if item["gold"]["difficulty"] == difficulty
            ])
            for difficulty in DIFFICULTIES
        },
        "representative_failures": [
            {
                "id": item["id"],
                "difficulty": item["gold"]["difficulty"],
                "incident_text": item["gold"]["incident_text"],
                "errors": item["evaluation"]["errors"],
                "expected_l1": item["gold"]["expected_l1"],
                "expected_l2": item["gold"].get("expected_l2"),
                "predicted_l1": item["actual"]["predicted_l1"],
                "predicted_l2": item["actual"]["predicted_l2"],
                "expected_coverages": item["gold"].get("expected_coverage_std_codes") or [],
                "actual_coverages": item["actual"]["coverage_std_codes"],
            }
            for item in failures[:10]
        ],
        "scenarios": outcomes,
    }


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path,
        default=backend_dir / "data/eval/claim_pipeline_gold.jsonl",
    )
    parser.add_argument(
        "--classifier-gold", type=Path,
        default=backend_dir / "data/eval/incidents_gold.jsonl",
        help="scenario 문구와 L1/L2가 기존 검수 gold에서 변조되지 않았는지 확인",
    )
    parser.add_argument(
        "--classifier-predictions", type=Path,
        default=backend_dir / "eval/results/incident_eval.json",
        help="기존 classifier 평가의 원시 예측 JSON",
    )
    parser.add_argument(
        "--output", type=Path,
        default=backend_dir / "eval/results/claim_pipeline_eval.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--gold-routing", action="store_true",
        help="분류기를 oracle로 고정해 downstream KB 경로만 격리 평가(모델 E2E 성능 아님)",
    )
    parser.add_argument("--live-classifier", action="store_true")
    parser.add_argument("--request-interval", type=float, default=4.2)
    parser.add_argument("--retry-wait", type=float, default=65.0)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--l1-threshold", type=float, default=classifier.DEFAULT_L1_AUTO_THRESHOLD)
    parser.add_argument("--l2-threshold", type=float, default=classifier.DEFAULT_L2_AUTO_THRESHOLD)
    args = parser.parse_args()

    rows = load_jsonl(args.dataset)
    classifier_gold_rows = load_jsonl(args.classifier_gold)
    db = SessionLocal()
    try:
        dataset_summary = validate_dataset(rows, db, classifier_gold_rows)
        if args.validate_only:
            report = {
                "evaluation_version": EVALUATION_VERSION,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "dataset_validated_no_pipeline_run",
                "dataset_sha256": dataset_sha256(rows),
                "dataset": dataset_summary,
                "metrics": None,
                "note": "구조·기존 classifier gold·실제 KB mapping만 검증했으며 성능 수치가 아니다.",
            }
        else:
            if args.gold_routing:
                predictions = [_scenario_prediction_from_gold(row) for row in rows]
                prediction_metadata = {"source": "gold-routing-oracle"}
                routing_mode = "gold-routing-downstream-isolation"
            elif args.live_classifier:
                live_rows = [
                    {"id": row["id"], "text": row["incident_text"], "answers": row.get("answers") or {}}
                    for row in rows
                ]
                predictions = collect_live_predictions(
                    live_rows,
                    request_interval=args.request_interval,
                    retry_wait=args.retry_wait,
                    checkpoint_path=args.checkpoint,
                )
                prediction_metadata = {
                    "source": "live", "model": config.GEMINI_MODEL,
                }
                routing_mode = "live-classifier-predictions"
            else:
                predictions, prediction_metadata = load_prediction_payload(args.classifier_predictions)
                routing_mode = "cached-classifier-predictions"
            report = build_report(
                rows, predictions, db,
                l1_threshold=args.l1_threshold,
                l2_threshold=args.l2_threshold,
                prediction_metadata=prediction_metadata,
                routing_mode=routing_mode,
            )
            report["dataset"].update(dataset_summary)
    finally:
        db.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"평가 결과 저장: {args.output}")
    printable = report.get("metrics") or report["dataset"]
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
