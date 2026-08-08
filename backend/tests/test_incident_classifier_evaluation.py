from eval.evaluate_incident_classifier import (
    L1_LABELS, evaluate_predictions, validate_dataset,
)


def test_metrics_treat_abstention_as_end_to_end_error_and_measure_it_separately():
    rows = [
        {"id": "a", "gold_l1": "PROP", "gold_l2": "PROP_THEFT", "expected_abstain": False},
        {"id": "b", "gold_l1": "TRV", "gold_l2": None, "expected_abstain": True},
    ]
    predictions = [
        {"id": "a", "predicted_l1": "PROP", "l1_confidence": 0.9, "predicted_l2": "PROP_THEFT", "l2_confidence": 0.9},
        {"id": "b", "predicted_l1": "TRV", "l1_confidence": 0.9, "predicted_l2": "TRV_FLIGHT_DELAY", "l2_confidence": 0.4},
    ]

    metrics = evaluate_predictions(rows, predictions, threshold=0.7)

    assert metrics["l1"]["accuracy_end_to_end"] == 1.0
    assert metrics["l2"]["accuracy_end_to_end"] == 1.0
    assert metrics["abstention"]["precision"] == 1.0
    assert metrics["abstention"]["recall"] == 1.0


def test_dataset_validator_requires_all_eight_l1_classes():
    rows = [
        {"id": code, "gold_l1": code, "difficulty": "easy", "expected_abstain": False}
        for code in L1_LABELS
    ]
    summary = validate_dataset(rows)
    assert summary["sample_count"] == 8
    assert set(summary["l1_counts"]) == set(L1_LABELS)
