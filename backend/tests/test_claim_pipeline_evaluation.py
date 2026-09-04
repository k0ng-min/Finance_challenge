"""청구지원 E2E golden set과 evaluator의 안전 계약."""
from pathlib import Path

from eval.evaluate_claim_pipeline import (
    _aggregate,
    build_report,
    load_jsonl,
    load_prediction_payload,
    validate_dataset,
)


BACKEND = Path(__file__).resolve().parents[1]
DATASET = BACKEND / "data/eval/claim_pipeline_gold.jsonl"
CLASSIFIER_GOLD = BACKEND / "data/eval/incidents_gold.jsonl"
CLASSIFIER_RESULTS = BACKEND / "eval/results/incident_eval.json"


def test_claim_pipeline_gold_is_40_reviewable_kb_grounded_scenarios(kb_session):
    rows = load_jsonl(DATASET)
    summary = validate_dataset(rows, kb_session, load_jsonl(CLASSIFIER_GOLD))

    assert summary["sample_count"] == 40
    assert summary["synthetic"] is True
    assert summary["l1_counts"] == {
        "CHG": 5, "EMG": 5, "ILL": 5, "INJ": 5,
        "LIA": 5, "PROP": 5, "SPC": 5, "TRV": 5,
    }
    assert summary["difficulty_counts"] == {"ambiguous": 8, "easy": 24, "hard": 8}
    assert summary["grounded_gold_clause_count"] > 0


def test_ambiguous_cases_do_not_force_a_single_l2_or_downstream_answer():
    ambiguous = [row for row in load_jsonl(DATASET) if row["difficulty"] == "ambiguous"]

    assert len(ambiguous) == 8
    for row in ambiguous:
        assert row["expected_l2"] is None
        assert row["expected_l2_abstain"] is True
        assert row["expected_coverage_std_codes"] == []
        assert row["expected_required_doc_codes"] == []
        assert row["expected_relations"] == []
        assert row["expected_unsupported"] is True


def test_cached_classifier_predictions_run_through_real_claim_pipeline(kb_session):
    rows = load_jsonl(DATASET)
    predictions, metadata = load_prediction_payload(CLASSIFIER_RESULTS)
    report = build_report(rows, predictions, kb_session, prediction_metadata=metadata)
    metrics = report["metrics"]

    assert metrics["sample_count"] == 40
    assert set(report["metrics_by_difficulty"]) == {"easy", "hard", "ambiguous"}
    assert metrics["citation_count"] > 0
    assert metrics["citation_grounding_rate"] == 1.0
    assert metrics["unsupported_recommendation_rate"] == 0.0
    assert metrics["coverage"]["precision"] >= 0.95
    assert metrics["coverage"]["recall"] == 1.0
    assert metrics["mandatory_document"]["precision"] >= 0.95
    assert metrics["mandatory_document"]["recall"] == 1.0
    assert metrics["end_to_end_exact_success_rate"] >= 0.9
    assert metrics["end_to_end_acceptable_success_rate"] >= 0.9

    by_id = {scenario["id"]: scenario for scenario in report["scenarios"]}

    # 명시적인 의료이송 문구는 현재 결정론적 보정으로 구조송환 경로를 탄다.
    medical_transport = by_id["EMG-005"]
    assert medical_transport["actual"]["predicted_l1"] == "EMG"
    assert medical_transport["actual"]["predicted_l2"] == "EMG_MEDICAL_TRANSPORT"
    assert medical_transport["evaluation"]["exact"] is True

    # 분류가 보류된 사고는 L1의 모든 하위 담보를 펼치지 않고 명시적 확인불가로 끝낸다.
    for scenario_id in ("SPC-015", "SPC-017"):
        abstained = by_id[scenario_id]
        assert abstained["actual"]["coverage_std_codes"] == []
        assert abstained["actual"]["mandatory_doc_codes"] == []
        assert abstained["actual"]["decisive_recommendation_count"] == 0
        assert abstained["actual"]["explicit_unsupported_result"] is True

    # 결과에 실제 인용문이 들어가며, evaluator가 clause substring 여부를 기록한다.
    citations = [
        citation
        for scenario in report["scenarios"]
        for citation in scenario["actual"]["citations"]
    ]
    assert citations
    assert all(citation["citation"] and citation["grounded"] for citation in citations)


def test_unsupported_recommendation_rate_counts_decisive_ungrounded_outputs():
    outcome = {
        "gold": {
            "expected_l1": "PROP",
            "expected_l2": "PROP_THEFT",
            "expected_l2_abstain": False,
            "expected_coverage_std_codes": ["PERSONAL_EFFECTS"],
            "expected_required_doc_codes": [],
        },
        "actual": {
            "predicted_l1": "PROP",
            "predicted_l2": "PROP_THEFT",
            "coverage_std_codes": ["PERSONAL_EFFECTS"],
            "mandatory_doc_codes": [],
            "citations": [],
            "decisive_recommendation_count": 1,
            "unsupported_recommendation_count": 1,
            "unsupported_result": False,
            "explicit_unsupported_result": False,
        },
        "evaluation": {"exact": False, "acceptable": False, "errors": ["unsupported_recommendation"]},
    }

    metrics = _aggregate([outcome])
    assert metrics["unsupported_recommendation_rate"] == 1.0
    assert metrics["unsupported_recommendation_count"] == 1
