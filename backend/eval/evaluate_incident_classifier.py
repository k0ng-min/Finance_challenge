"""골드셋 기반 사고유형 분류 평가.

라이브 실행은 Gemini 원시 예측을 JSON으로 캐시한 뒤, 같은 예측에 여러 confidence 임계값을
적용한다. 따라서 threshold sweep이 API를 중복 호출하지 않고 재현 가능하다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app import config
from app.database import SessionLocal
from app.services import incident_classify_gemini as classifier

EVALUATION_VERSION = "incident-eval-v2"
L1_LABELS = tuple(classifier.L1_DESCRIPTIONS)
THRESHOLDS = tuple(round(0.40 + 0.05 * i, 2) for i in range(9))


def prompt_sha256() -> str:
    return hashlib.sha256((classifier._L1_PROMPT + classifier._L2_PROMPT).encode("utf-8")).hexdigest()


def dataset_sha256(rows: list[dict]) -> str:
    canonical = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("gold_l1") not in L1_LABELS:
            raise ValueError(f"{path}:{line_no}: 잘못된 gold_l1={row.get('gold_l1')!r}")
        rows.append(row)
    return rows


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _round(value: float) -> float:
    return round(value, 4)


def accuracy(y_true: list[str], y_pred: list[str | None]) -> float:
    return _round(_safe_div(sum(a == b for a, b in zip(y_true, y_pred)), len(y_true)))


def macro_f1(y_true: list[str], y_pred: list[str | None], labels: Iterable[str]) -> float:
    scores = []
    for label in labels:
        tp = sum(t == label and p == label for t, p in zip(y_true, y_pred))
        fp = sum(t != label and p == label for t, p in zip(y_true, y_pred))
        fn = sum(t == label and p != label for t, p in zip(y_true, y_pred))
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        scores.append(_safe_div(2 * precision * recall, precision + recall))
    return _round(_safe_div(sum(scores), len(scores)))


def confusion_matrix(
    y_true: list[str], y_pred: list[str | None], labels: Iterable[str]
) -> dict[str, dict[str, int]]:
    ordered = list(labels)
    columns = ordered + ["ABSTAIN"]
    matrix = {truth: {prediction: 0 for prediction in columns} for truth in ordered}
    for truth, prediction in zip(y_true, y_pred):
        matrix[truth][prediction if prediction in ordered else "ABSTAIN"] += 1
    return matrix


def binary_metrics(y_true: list[bool], y_pred: list[bool]) -> dict[str, float | int]:
    tp = sum(t and p for t, p in zip(y_true, y_pred))
    fp = sum(not t and p for t, p in zip(y_true, y_pred))
    fn = sum(t and not p for t, p in zip(y_true, y_pred))
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return {
        "precision": _round(precision),
        "recall": _round(recall),
        "f1": _round(_safe_div(2 * precision * recall, precision + recall)),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
    }


def _expected_l1_abstain(row: dict) -> bool:
    return bool(row.get("expected_l1_abstain", False))


def _expected_l2_abstain(row: dict) -> bool:
    return bool(row.get("expected_l2_abstain", row.get("expected_abstain", False)))


def evaluate_predictions(
    rows: list[dict], predictions: list[dict], l1_threshold: float, l2_threshold: float,
) -> dict:
    if len(rows) != len(predictions):
        raise ValueError(f"gold {len(rows)}건과 prediction {len(predictions)}건의 수가 다릅니다")

    by_id = {item["id"]: item for item in predictions}
    if len(by_id) != len(predictions):
        raise ValueError("prediction id가 중복되었습니다")
    missing_ids = [row["id"] for row in rows if row["id"] not in by_id]
    if missing_ids:
        raise ValueError(f"prediction이 없는 id: {', '.join(missing_ids[:5])}")
    ordered_predictions = [by_id[row["id"]] for row in rows]

    l1_pred_all = [
        pred.get("predicted_l1")
        if float(pred.get("l1_confidence", 0.0)) >= l1_threshold else None
        for pred in ordered_predictions
    ]
    l2_pred_all: list[str | None] = []
    for pred, final_l1 in zip(ordered_predictions, l1_pred_all):
        raw_l2 = pred.get("predicted_l2")
        l2 = (
            raw_l2
            if final_l1 and raw_l2 and float(pred.get("l2_confidence", 0.0)) >= l2_threshold
            else None
        )
        l2_pred_all.append(l2)

    l1_indices = [i for i, row in enumerate(rows) if not _expected_l1_abstain(row)]
    l1_true = [rows[i]["gold_l1"] for i in l1_indices]
    l1_pred = [l1_pred_all[i] for i in l1_indices]

    l2_indices = [
        i for i, row in enumerate(rows)
        if row.get("gold_l2") and not _expected_l2_abstain(row)
    ]
    l2_true = [rows[i]["gold_l2"] for i in l2_indices]
    l2_pred = [l2_pred_all[i] for i in l2_indices]
    l2_labels = sorted(set(l2_true))

    conditional_indices = [i for i in l2_indices if l1_pred_all[i] == rows[i]["gold_l1"]]
    conditional_true = [rows[i]["gold_l2"] for i in conditional_indices]
    conditional_pred = [l2_pred_all[i] for i in conditional_indices]

    expected_l1_abstain = [_expected_l1_abstain(row) for row in rows]
    expected_l2_abstain = [_expected_l2_abstain(row) for row in rows]
    predicted_l1_abstain = [value is None for value in l1_pred_all]
    predicted_l2_abstain = [value is None for value in l2_pred_all]
    return {
        "thresholds": {"l1": l1_threshold, "l2": l2_threshold},
        "sample_count": len(rows),
        "l1": {
            "evaluated_count": len(l1_indices),
            "accuracy_end_to_end": accuracy(l1_true, l1_pred),
            "macro_f1_end_to_end": macro_f1(l1_true, l1_pred, L1_LABELS),
            "coverage": _round(_safe_div(sum(value is not None for value in l1_pred), len(l1_pred))),
            "confusion_matrix": confusion_matrix(l1_true, l1_pred, L1_LABELS),
        },
        "l2": {
            "evaluated_count": len(l2_indices),
            "accuracy_end_to_end": accuracy(l2_true, l2_pred),
            "macro_f1_end_to_end": macro_f1(l2_true, l2_pred, l2_labels),
            "accuracy_given_correct_l1": accuracy(conditional_true, conditional_pred),
            "macro_f1_given_correct_l1": macro_f1(conditional_true, conditional_pred, l2_labels),
            "conditional_count": len(conditional_indices),
            "confusion_matrix": confusion_matrix(l2_true, l2_pred, l2_labels),
        },
        "abstention": {
            "l1": binary_metrics(expected_l1_abstain, predicted_l1_abstain),
            "l2": binary_metrics(expected_l2_abstain, predicted_l2_abstain),
        },
    }


def split_dataset(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """L1별 정렬 후 교대로 10/10을 나눠 난이도 쏠림 없는 고정 split을 만든다."""
    explicit = [row.get("split") for row in rows]
    if any(explicit) and not all(explicit):
        raise ValueError("split 필드는 모든 행에 넣거나 모든 행에서 생략해야 합니다")
    if all(explicit):
        calibration = [row for row in rows if row["split"] == "calibration"]
        evaluation = [row for row in rows if row["split"] == "evaluation"]
        if len(calibration) + len(evaluation) != len(rows):
            raise ValueError("split은 calibration 또는 evaluation이어야 합니다")
        return calibration, evaluation

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["gold_l1"]].append(row)
    calibration, evaluation = [], []
    for label in L1_LABELS:
        for index, row in enumerate(sorted(grouped[label], key=lambda item: item["id"])):
            (calibration if index % 2 == 0 else evaluation).append(row)
    return calibration, evaluation


def validate_dataset(rows: list[dict]) -> dict:
    l1_counts = Counter(row["gold_l1"] for row in rows)
    difficulties = Counter(row.get("difficulty") for row in rows)
    missing = [label for label in L1_LABELS if not l1_counts[label]]
    if missing:
        raise ValueError(f"골드셋에 없는 L1 클래스: {', '.join(missing)}")
    ids = [row.get("id") for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("골드셋 id가 중복되었습니다")
    invalid_l1_abstain = [row["id"] for row in rows if _expected_l1_abstain(row) and not _expected_l2_abstain(row)]
    if invalid_l1_abstain:
        raise ValueError("L1 abstain 사례는 L2도 abstain이어야 합니다")
    invalid_l2_gold = [row["id"] for row in rows if _expected_l2_abstain(row) and row.get("gold_l2")]
    if invalid_l2_gold:
        raise ValueError("L2 abstain 사례의 gold_l2는 null이어야 합니다")
    calibration, evaluation = split_dataset(rows)
    return {
        "sample_count": len(rows),
        "l1_counts": dict(sorted(l1_counts.items())),
        "difficulty_counts": dict(sorted(difficulties.items())),
        "split_counts": {"calibration": len(calibration), "evaluation": len(evaluation)},
        "split_l1_counts": {
            "calibration": dict(sorted(Counter(row["gold_l1"] for row in calibration).items())),
            "evaluation": dict(sorted(Counter(row["gold_l1"] for row in evaluation).items())),
        },
        "expected_l1_abstain_count": sum(_expected_l1_abstain(row) for row in rows),
        "expected_l2_abstain_count": sum(_expected_l2_abstain(row) for row in rows),
    }


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc)
    return getattr(exc, "status_code", None) == 429 or "429" in message or "RESOURCE_EXHAUSTED" in message


def collect_live_predictions(
    rows: list[dict], *, request_interval: float = 4.2, retry_wait: float = 65.0,
    checkpoint_path: Path | None = None,
) -> list[dict]:
    if not config.GEMINI_ENABLED:
        raise RuntimeError("GEMINI_API_KEY가 없어 라이브 예측을 수집할 수 없습니다")
    db = SessionLocal()
    predictions: list[dict] = []
    if checkpoint_path and checkpoint_path.exists():
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            if payload.get("model") not in (None, config.GEMINI_MODEL):
                raise ValueError("checkpoint 모델이 현재 설정과 다릅니다")
            if payload.get("prompt_sha256") not in (None, prompt_sha256()):
                raise ValueError("checkpoint 프롬프트가 현재 코드와 다릅니다")
            if payload.get("dataset_sha256") not in (None, dataset_sha256(rows)):
                raise ValueError("checkpoint 골드셋이 현재 데이터와 다릅니다")
            predictions = payload.get("predictions", [])
        else:
            predictions = payload
    completed_ids = {prediction["id"] for prediction in predictions}
    last_request_at: float | None = None

    def _request(callable_):
        nonlocal last_request_at
        for attempt in range(1, 6):
            if last_request_at is not None:
                time.sleep(max(0.0, request_interval - (time.monotonic() - last_request_at)))
            last_request_at = time.monotonic()
            try:
                return callable_()
            except Exception as exc:
                if not _is_rate_limit_error(exc) or attempt == 5:
                    raise
                print(f"429 rate limit - retry in {retry_wait:.0f}s ({attempt}/5)", flush=True)
                time.sleep(retry_wait)

    try:
        for index, row in enumerate(rows, 1):
            if row["id"] in completed_ids:
                print(f"[{index}/{len(rows)}] {row['id']} (checkpoint)", flush=True)
                continue
            l1_code, l1_confidence, l1_reason = _request(
                lambda: classifier.classify_l1(row["text"], raise_on_error=True)
            )
            l2_result = _request(
                lambda: classifier.classify_l2(
                    db, l1_code, row["text"], row.get("answers") or {},
                    auto_threshold=0.0, raise_on_error=True,
                )
            )
            predictions.append({
                "id": row["id"],
                "predicted_l1": l1_code,
                "l1_confidence": l1_confidence,
                "l1_reason": l1_reason,
                "predicted_l2": l2_result.l2_code,
                "l2_confidence": l2_result.confidence,
                "l2_reason": l2_result.reason,
            })
            if checkpoint_path:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                checkpoint_path.write_text(
                    json.dumps({
                        "evaluation_version": EVALUATION_VERSION,
                        "model": config.GEMINI_MODEL,
                        "prompt_sha256": prompt_sha256(),
                        "dataset_sha256": dataset_sha256(rows),
                        "predictions": predictions,
                    }, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            print(f"[{index}/{len(rows)}] {row['id']}", flush=True)
    finally:
        db.close()
    return predictions


def build_report(rows: list[dict], predictions: list[dict]) -> dict:
    predictions_by_id = {prediction["id"]: prediction for prediction in predictions}
    calibration_rows, evaluation_rows = split_dataset(rows)
    calibration_predictions = [predictions_by_id[row["id"]] for row in calibration_rows]
    evaluation_predictions = [predictions_by_id[row["id"]] for row in evaluation_rows]
    sweep = [
        evaluate_predictions(
            calibration_rows, calibration_predictions,
            l1_threshold=l1_threshold, l2_threshold=l2_threshold,
        )
        for l1_threshold in THRESHOLDS
        for l2_threshold in THRESHOLDS
    ]
    selected = max(
        sweep,
        key=lambda item: (
            item["abstention"]["l1"]["f1"]
            + item["abstention"]["l2"]["f1"]
            + item["l2"]["macro_f1_end_to_end"],
            item["abstention"]["l1"]["recall"] + item["abstention"]["l2"]["recall"],
            item["thresholds"]["l1"] + item["thresholds"]["l2"],
        ),
    )
    selected_thresholds = selected["thresholds"]
    held_out_metrics = evaluate_predictions(
        evaluation_rows, evaluation_predictions,
        l1_threshold=selected_thresholds["l1"], l2_threshold=selected_thresholds["l2"],
    )
    operating_metrics = evaluate_predictions(
        evaluation_rows, evaluation_predictions,
        l1_threshold=classifier.DEFAULT_L1_AUTO_THRESHOLD,
        l2_threshold=classifier.DEFAULT_L2_AUTO_THRESHOLD,
    )
    grid_summary = [
        {
            "thresholds": item["thresholds"],
            "l1_accuracy": item["l1"]["accuracy_end_to_end"],
            "l1_macro_f1": item["l1"]["macro_f1_end_to_end"],
            "l2_accuracy": item["l2"]["accuracy_end_to_end"],
            "l2_macro_f1": item["l2"]["macro_f1_end_to_end"],
            "l1_abstention_f1": item["abstention"]["l1"]["f1"],
            "l1_abstention_recall": item["abstention"]["l1"]["recall"],
            "l2_abstention_f1": item["abstention"]["l2"]["f1"],
            "l2_abstention_recall": item["abstention"]["l2"]["recall"],
        }
        for item in sweep
    ]
    return {
        "evaluation_version": EVALUATION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": config.GEMINI_MODEL,
        "prompt_sha256": prompt_sha256(),
        "dataset_sha256": dataset_sha256(rows),
        "dataset": validate_dataset(rows),
        "selection_rule": (
            "calibration 80건에서 max(l1_abstention_f1 + l2_abstention_f1 + "
            "l2_macro_f1_end_to_end), then abstention recall, then safer thresholds"
        ),
        "selected_thresholds": selected_thresholds,
        "calibration_selected_metrics": selected,
        "held_out_evaluation_metrics": held_out_metrics,
        "operating_thresholds": {
            "l1": classifier.DEFAULT_L1_AUTO_THRESHOLD,
            "l2": classifier.DEFAULT_L2_AUTO_THRESHOLD,
        },
        "held_out_operating_metrics": operating_metrics,
        "calibration_threshold_grid": grid_summary,
        "predictions": predictions,
    }


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=backend_dir / "data/eval/incidents_gold.jsonl")
    parser.add_argument("--predictions", type=Path, help="기존 원시 예측 JSON 재사용")
    parser.add_argument("--output", type=Path, default=backend_dir / "eval/results/incident_eval.json")
    parser.add_argument("--validate-only", action="store_true", help="API 호출 없이 골드셋 구조만 검증")
    parser.add_argument("--request-interval", type=float, default=4.2, help="Gemini 요청 사이 최소 간격(초)")
    parser.add_argument("--retry-wait", type=float, default=65.0, help="429 응답 후 재시도 대기(초)")
    parser.add_argument("--checkpoint", type=Path, help="완료된 원시 예측을 매 사례 저장하고 재시작 시 재사용")
    args = parser.parse_args()

    rows = load_jsonl(args.dataset)
    dataset_summary = validate_dataset(rows)
    if args.validate_only:
        report = {
            "evaluation_version": EVALUATION_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "dataset_validated_no_live_predictions",
            "model": config.GEMINI_MODEL,
            "prompt_sha256": prompt_sha256(),
            "dataset_sha256": dataset_sha256(rows),
            "dataset": dataset_summary,
            "metrics": None,
            "note": "Gemini API 예측을 실행하지 않은 구조 검증 결과이며 모델 성능 수치가 아닙니다.",
        }
    elif args.predictions:
        payload = json.loads(args.predictions.read_text(encoding="utf-8"))
        predictions = payload.get("predictions", payload)
        report = build_report(rows, predictions)
    else:
        predictions = collect_live_predictions(
            rows, request_interval=args.request_interval,
            retry_wait=args.retry_wait, checkpoint_path=args.checkpoint,
        )
        report = build_report(rows, predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"평가 결과 저장: {args.output}")
    print(json.dumps(report.get("held_out_evaluation_metrics", report["dataset"]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
