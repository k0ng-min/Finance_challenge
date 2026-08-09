from eval.evaluate_incident_classifier import (
    L1_LABELS, build_report, dataset_sha256, evaluate_predictions, split_dataset,
    validate_dataset,
)


def test_metrics_treat_abstention_as_end_to_end_error_and_measure_it_separately():
    rows = [
        {"id": "a", "gold_l1": "PROP", "gold_l2": "PROP_THEFT", "expected_l1_abstain": False, "expected_l2_abstain": False},
        {"id": "b", "gold_l1": "TRV", "gold_l2": None, "expected_l1_abstain": True, "expected_l2_abstain": True},
    ]
    predictions = [
        {"id": "a", "predicted_l1": "PROP", "l1_confidence": 0.9, "predicted_l2": "PROP_THEFT", "l2_confidence": 0.9},
        {"id": "b", "predicted_l1": "TRV", "l1_confidence": 0.4, "predicted_l2": "TRV_FLIGHT_DELAY", "l2_confidence": 0.4},
    ]

    metrics = evaluate_predictions(rows, predictions, l1_threshold=0.7, l2_threshold=0.7)

    assert metrics["l1"]["accuracy_end_to_end"] == 1.0
    assert metrics["l2"]["accuracy_end_to_end"] == 1.0
    assert metrics["abstention"]["l1"]["precision"] == 1.0
    assert metrics["abstention"]["l1"]["recall"] == 1.0
    assert metrics["abstention"]["l2"]["precision"] == 1.0
    assert metrics["abstention"]["l2"]["recall"] == 1.0


def test_dataset_validator_requires_all_eight_l1_classes():
    rows = [
        {
            "id": code, "gold_l1": code, "difficulty": "easy",
            "expected_l1_abstain": False, "expected_l2_abstain": False,
        }
        for code in L1_LABELS
    ]
    summary = validate_dataset(rows)
    assert summary["sample_count"] == 8
    assert set(summary["l1_counts"]) == set(L1_LABELS)


def test_l1_and_l2_thresholds_are_applied_independently():
    rows = [{
        "id": "a", "gold_l1": "PROP", "gold_l2": "PROP_THEFT",
        "expected_l1_abstain": False, "expected_l2_abstain": False,
    }]
    predictions = [{
        "id": "a", "predicted_l1": "PROP", "l1_confidence": 0.60,
        "predicted_l2": "PROP_THEFT", "l2_confidence": 0.75,
    }]

    l1_strict = evaluate_predictions(rows, predictions, l1_threshold=0.65, l2_threshold=0.70)
    l2_strict = evaluate_predictions(rows, predictions, l1_threshold=0.55, l2_threshold=0.80)

    assert l1_strict["l1"]["coverage"] == 0.0
    assert l2_strict["l1"]["coverage"] == 1.0
    assert l2_strict["l2"]["accuracy_end_to_end"] == 0.0


def test_report_selects_on_calibration_and_reports_on_held_out_set():
    rows = []
    predictions = []
    for code in L1_LABELS:
        for number in range(1, 21):
            row_id = f"{code}-{number:03d}"
            l2_code = f"{code}_TEST"
            rows.append({
                "id": row_id, "gold_l1": code, "gold_l2": l2_code,
                "difficulty": "easy", "expected_l1_abstain": False,
                "expected_l2_abstain": False,
            })
            predictions.append({
                "id": row_id, "predicted_l1": code, "l1_confidence": 0.70,
                "predicted_l2": l2_code, "l2_confidence": 0.70,
            })

    calibration, evaluation = split_dataset(rows)
    report = build_report(rows, predictions)

    assert len(calibration) == len(evaluation) == 80
    assert len(report["calibration_threshold_grid"]) == 81
    assert report["selected_thresholds"] == {"l1": 0.7, "l2": 0.7}
    assert report["held_out_evaluation_metrics"]["sample_count"] == 80
    assert report["dataset_sha256"] == dataset_sha256(rows)
    assert len(report["dataset_sha256"]) == 64
