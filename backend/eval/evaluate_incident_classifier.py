"""골드셋 기반 사고유형 분류 평가.

라이브 실행은 Gemini 원시 예측을 JSON으로 캐시한 뒤, 같은 예측에 여러 confidence 임계값을
적용한다. 따라서 threshold sweep이 API를 중복 호출하지 않고 재현 가능하다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app import config
from app.database import SessionLocal
from app.services import incident_classify_gemini as classifier

EVALUATION_VERSION = "incident-eval-v1"
L1_LABELS = tuple(classifier.L1_DESCRIPTIONS)
THRESHOLDS = tuple(round(0.40 + 0.05 * i, 2) for i in range(9))


def prompt_sha256() -> str:
    return hashlib.sha256((classifier._L1_PROMPT + classifier._L2_PROMPT).encode("utf-8")).hexdigest()


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


def evaluate_predictions(rows: list[dict], predictions: list[dict], threshold: float) -> dict:
    if len(rows) != len(predictions):
        raise ValueError(f"gold {len(rows)}건과 prediction {len(predictions)}건의 수가 다릅니다")

    by_id = {item["id"]: item for item in predictions}
    ordered_predictions = [by_id[row["id"]] for row in rows]

    l1_true = [row["gold_l1"] for row in rows]
    l1_pred = [
        pred.get("predicted_l1") if float(pred.get("l1_confidence", 0.0)) >= threshold else None
        for pred in ordered_predictions
    ]
    predicted_abstain = []
    l2_pred_all: list[str | None] = []
    for pred, final_l1 in zip(ordered_predictions, l1_pred):
        raw_l2 = pred.get("predicted_l2")
        l2 = raw_l2 if final_l1 and raw_l2 and float(pred.get("l2_confidence", 0.0)) >= threshold else None
        l2_pred_all.append(l2)
        predicted_abstain.append(l2 is None)

    l2_indices = [i for i, row in enumerate(rows) if row.get("gold_l2")]
    l2_true = [rows[i]["gold_l2"] for i in l2_indices]
    l2_pred = [l2_pred_all[i] for i in l2_indices]
    l2_labels = sorted(set(l2_true))

    conditional_indices = [i for i in l2_indices if l1_pred[i] == rows[i]["gold_l1"]]
    conditional_true = [rows[i]["gold_l2"] for i in conditional_indices]
    conditional_pred = [l2_pred_all[i] for i in conditional_indices]

    expected_abstain = [bool(row.get("expected_abstain", False)) for row in rows]
    return {
        "threshold": threshold,
        "sample_count": len(rows),
        "l1": {
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
        "abstention": binary_metrics(expected_abstain, predicted_abstain),
    }


def validate_dataset(rows: list[dict]) -> dict:
    l1_counts = Counter(row["gold_l1"] for row in rows)
    difficulties = Counter(row.get("difficulty") for row in rows)
    missing = [label for label in L1_LABELS if not l1_counts[label]]
    if missing:
        raise ValueError(f"골드셋에 없는 L1 클래스: {', '.join(missing)}")
    return {
        "sample_count": len(rows),
        "l1_counts": dict(sorted(l1_counts.items())),
        "difficulty_counts": dict(sorted(difficulties.items())),
        "expected_abstain_count": sum(bool(row.get("expected_abstain")) for row in rows),
    }


def collect_live_predictions(rows: list[dict]) -> list[dict]:
    if not config.GEMINI_ENABLED:
        raise RuntimeError("GEMINI_API_KEY가 없어 라이브 예측을 수집할 수 없습니다")
    db = SessionLocal()
    predictions = []
    try:
        for index, row in enumerate(rows, 1):
            l1_code, l1_confidence, l1_reason = classifier.classify_l1(row["text"])
            l2_result = classifier.classify_l2(
                db, l1_code, row["text"], row.get("answers") or {}, auto_threshold=0.0,
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
            print(f"[{index}/{len(rows)}] {row['id']}")
    finally:
        db.close()
    return predictions


def build_report(rows: list[dict], predictions: list[dict]) -> dict:
    sweep = [evaluate_predictions(rows, predictions, threshold) for threshold in THRESHOLDS]
    selected = max(
        sweep,
        key=lambda item: (
            item["abstention"]["f1"] + item["l2"]["macro_f1_end_to_end"],
            item["abstention"]["recall"],
            item["threshold"],
        ),
    )
    return {
        "evaluation_version": EVALUATION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": config.GEMINI_MODEL,
        "prompt_sha256": prompt_sha256(),
        "dataset": validate_dataset(rows),
        "selection_rule": "max(abstention_f1 + l2_macro_f1_end_to_end), then recall, then safer threshold",
        "selected_threshold": selected["threshold"],
        "selected_metrics": selected,
        "threshold_sweep": sweep,
        "predictions": predictions,
    }


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=backend_dir / "data/eval/incidents_gold.jsonl")
    parser.add_argument("--predictions", type=Path, help="기존 원시 예측 JSON 재사용")
    parser.add_argument("--output", type=Path, default=backend_dir / "eval/results/incident_eval.json")
    parser.add_argument("--validate-only", action="store_true", help="API 호출 없이 골드셋 구조만 검증")
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
            "dataset": dataset_summary,
            "metrics": None,
            "note": "Gemini API 예측을 실행하지 않은 구조 검증 결과이며 모델 성능 수치가 아닙니다.",
        }
    elif args.predictions:
        payload = json.loads(args.predictions.read_text(encoding="utf-8"))
        predictions = payload.get("predictions", payload)
        report = build_report(rows, predictions)
    else:
        predictions = collect_live_predictions(rows)
        report = build_report(rows, predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"평가 결과 저장: {args.output}")
    print(json.dumps(report.get("selected_metrics", report["dataset"]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
