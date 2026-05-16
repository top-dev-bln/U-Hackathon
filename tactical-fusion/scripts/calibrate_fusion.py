from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tactical_fusion.config import DEFAULT_CALIBRATION_CONFIG, resolve_calibration_config
from tactical_fusion.fusion import fuse_signals
from tactical_fusion.ingestion import load_json_file, validate_input1, validate_input2
from tactical_fusion.normalization import normalize_input1, normalize_input2
from tactical_fusion.normalization.taxonomy import CATEGORIES

CATEGORY_ORDER = sorted(CATEGORIES)


def _severity_band(score: float, thresholds: dict[str, float]) -> str:
    if score >= thresholds["critical"]:
        return "critical"
    if score >= thresholds["high"]:
        return "high"
    if score >= thresholds["medium"]:
        return "medium"
    return "low"


def _float_range(start: float, end: float, step: float) -> list[float]:
    values: list[float] = []
    current = start
    while current <= end + 1e-9:
        values.append(round(current, 4))
        current += step
    return values


def _load_labels(labels_path: Path) -> dict[str, dict[str, Any]]:
    labels_map: dict[str, dict[str, Any]] = {}
    with labels_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            labels_map[str(row["sample_id"])] = row
    return labels_map


def _build_dataset(dataset_dir: Path) -> list[dict[str, Any]]:
    manifest_path = dataset_dir / "manifest.csv"
    labels_path = dataset_dir / "labels.jsonl"
    labels_map = _load_labels(labels_path)
    rows: list[dict[str, Any]] = []

    with manifest_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for manifest_row in reader:
            sample_id = str(manifest_row["sample_id"])
            labels_row = labels_map.get(sample_id)
            if labels_row is None:
                continue

            input1 = load_json_file(dataset_dir / manifest_row["input1_path"])
            input2 = load_json_file(dataset_dir / manifest_row["input2_path"])
            validate_input1(input1)
            validate_input2(input2)

            category_labels = labels_row.get("category_labels", [])
            true_severity: dict[str, float] = {}
            true_band: dict[str, str] = {}
            for item in category_labels:
                category = str(item.get("category", ""))
                if category not in CATEGORIES:
                    continue
                true_severity[category] = float(item.get("true_severity", 0.0))
                true_band[category] = str(item.get("severity_band", "low"))

            if not true_severity:
                continue

            rows.append(
                {
                    "sample_id": sample_id,
                    "split": manifest_row.get("split", "train"),
                    "baseline_signals": normalize_input1(input1),
                    "decision_signals": normalize_input2(input2),
                    "true_severity": true_severity,
                    "true_band": true_band,
                    "true_top_rank": labels_row.get("top_problems_rank", []),
                }
            )

    return rows


def _evaluate(samples: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, float]:
    if not samples:
        return {
            "mae": 0.0,
            "band_accuracy": 0.0,
            "top1_accuracy": 0.0,
            "top3_recall": 0.0,
            "objective": 999.0,
            "samples": 0,
        }

    thresholds = config["severity_thresholds"]
    mae_sum = 0.0
    total_points = 0
    band_correct = 0
    top1_correct = 0
    top3_recall_sum = 0.0

    for sample in samples:
        fused = fuse_signals(
            sample["baseline_signals"],
            sample["decision_signals"],
            baseline_weight=config["baseline_weight"],
            decision_weight=config["decision_weight"],
        )
        pred_map = {row.category: row.combined_score for row in fused}

        for category in CATEGORY_ORDER:
            pred = float(pred_map.get(category, 0.0))
            true = float(sample["true_severity"].get(category, 0.0))
            mae_sum += abs(pred - true)
            total_points += 1

            pred_band = _severity_band(pred, thresholds)
            true_band = sample["true_band"].get(category, _severity_band(true, thresholds))
            if pred_band == true_band:
                band_correct += 1

        pred_rank = sorted(
            ((category, float(pred_map.get(category, 0.0))) for category in CATEGORY_ORDER),
            key=lambda kv: kv[1],
            reverse=True,
        )
        pred_top1 = pred_rank[0][0]
        pred_top3 = {category for category, _ in pred_rank[:3]}

        true_top_rank = sample["true_top_rank"]
        if true_top_rank:
            true_top1 = str(true_top_rank[0])
            true_top3 = {str(item) for item in true_top_rank[:3]}
        else:
            true_sorted = sorted(
                sample["true_severity"].items(),
                key=lambda kv: kv[1],
                reverse=True,
            )
            true_top1 = true_sorted[0][0]
            true_top3 = {category for category, _ in true_sorted[:3]}

        if pred_top1 == true_top1:
            top1_correct += 1

        if true_top3:
            top3_recall_sum += len(pred_top3.intersection(true_top3)) / len(true_top3)

    mae = mae_sum / max(1, total_points)
    band_accuracy = band_correct / max(1, total_points)
    top1_accuracy = top1_correct / max(1, len(samples))
    top3_recall = top3_recall_sum / max(1, len(samples))

    objective = mae + (1.0 - band_accuracy) * 0.25 + (1.0 - top1_accuracy) * 0.2 + (1.0 - top3_recall) * 0.15
    return {
        "mae": round(mae, 6),
        "band_accuracy": round(band_accuracy, 6),
        "top1_accuracy": round(top1_accuracy, 6),
        "top3_recall": round(top3_recall, 6),
        "objective": round(objective, 6),
        "samples": len(samples),
    }


def _split_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_split = {"train": [], "val": [], "test": []}
    for row in rows:
        split = str(row.get("split", "train")).lower()
        if split not in by_split:
            split = "train"
        by_split[split].append(row)
    return by_split


def _grid_search(train_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, float], int]:
    best_config = resolve_calibration_config(None)
    best_metrics = _evaluate(train_rows, best_config)
    best_objective = best_metrics["objective"]
    iterations = 0

    baseline_values = _float_range(0.3, 0.75, 0.05)
    medium_values = _float_range(0.35, 0.5, 0.05)
    high_values = _float_range(0.55, 0.75, 0.05)
    critical_values = _float_range(0.75, 0.9, 0.05)

    for baseline_weight in baseline_values:
        for medium in medium_values:
            for high in high_values:
                if high <= medium:
                    continue
                for critical in critical_values:
                    if critical <= high:
                        continue
                    iterations += 1
                    candidate = resolve_calibration_config(
                        {
                            "baseline_weight": baseline_weight,
                            "decision_weight": 1.0 - baseline_weight,
                            "severity_thresholds": {
                                "medium": medium,
                                "high": high,
                                "critical": critical,
                            },
                        }
                    )
                    metrics = _evaluate(train_rows, candidate)
                    if metrics["objective"] < best_objective:
                        best_objective = metrics["objective"]
                        best_config = candidate
                        best_metrics = metrics
    return best_config, best_metrics, iterations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate tactical fusion weights and severity thresholds.")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("dataset") / "mock_100",
        help="Directory containing manifest.csv, labels.jsonl and samples/",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Calibration report output path (JSON). Default: <dataset-dir>/calibration_result.json",
    )
    parser.add_argument(
        "--export-config",
        type=Path,
        default=Path("tactical_fusion") / "calibration_config.json",
        help="Path to write best config JSON for runtime use.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_dir = args.dataset_dir
    output_path = args.output or (dataset_dir / "calibration_result.json")

    rows = _build_dataset(dataset_dir)
    split_rows = _split_rows(rows)

    train_rows = split_rows["train"]
    val_rows = split_rows["val"]
    test_rows = split_rows["test"]

    best_config, train_metrics, iterations = _grid_search(train_rows)
    val_metrics = _evaluate(val_rows, best_config)
    test_metrics = _evaluate(test_rows, best_config)

    default_config = resolve_calibration_config(DEFAULT_CALIBRATION_CONFIG)
    baseline_val = _evaluate(val_rows, default_config)
    baseline_test = _evaluate(test_rows, default_config)

    result = {
        "generated_at": "2026-04-25",
        "dataset_dir": str(dataset_dir),
        "search": {
            "iterations": iterations,
            "baseline_weight_range": [0.3, 0.75, 0.05],
            "medium_threshold_range": [0.35, 0.5, 0.05],
            "high_threshold_range": [0.55, 0.75, 0.05],
            "critical_threshold_range": [0.75, 0.9, 0.05],
        },
        "best_config": best_config,
        "metrics": {
            "train": train_metrics,
            "val": val_metrics,
            "test": test_metrics,
            "baseline_default": {
                "val": baseline_val,
                "test": baseline_test,
            },
        },
        "dataset_split_counts": {
            "train": len(train_rows),
            "val": len(val_rows),
            "test": len(test_rows),
            "total": len(rows),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    args.export_config.parent.mkdir(parents=True, exist_ok=True)
    with args.export_config.open("w", encoding="utf-8") as f:
        json.dump(best_config, f, indent=2, ensure_ascii=False)

    print(f"Calibration report written to: {output_path.resolve()}")
    print(f"Best runtime config written to: {args.export_config.resolve()}")
    print(f"Train objective: {train_metrics['objective']}")
    print(f"Val objective: {val_metrics['objective']} (default: {baseline_val['objective']})")
    print(f"Test objective: {test_metrics['objective']} (default: {baseline_test['objective']})")


if __name__ == "__main__":
    main()
