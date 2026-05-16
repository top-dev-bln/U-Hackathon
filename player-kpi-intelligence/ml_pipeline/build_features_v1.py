from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data" / "player_day_features.csv"
FEATURE_DIR = PROJECT_ROOT / "features"
OUTPUT_FILE = FEATURE_DIR / "features_v1.csv"
DICTIONARY_FILE = PROJECT_ROOT / "features_dictionary.md"

WINDOWS = [3, 7, 14, 21, 28]
BASE_METRICS = [
    "distance_m",
    "duration_min",
    "distance_per_min",
    "high_int_acc_abs_m",
    "high_int_dec_abs_m",
    "high_speed_distance_m",
    "high_speed_share_pct",
    "power_metabolic_avg_wkg",
    "sprints_count_per_min",
    "training_load_proxy",
    "accel_total_count",
]
Z_SCORE_METRICS = [
    "distance_m",
    "duration_min",
    "distance_per_min",
    "high_int_acc_abs_m",
    "high_speed_share_pct",
    "training_load_proxy",
]
EWMA_METRICS = ["distance_m", "high_int_acc_abs_m", "training_load_proxy"]
EWMA_SPANS = [7, 28]


def as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (float, int)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return default


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mu = mean(values)
    var = sum((x - mu) ** 2 for x in values) / len(values)
    return math.sqrt(var)


def rolling_slice(values: list[float], idx: int, window: int) -> list[float]:
    start = max(0, idx - window + 1)
    return values[start : idx + 1]


def parse_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parsed: dict[str, object] = dict(row)
            parsed["wy_id"] = int(float(str(row.get("wy_id", "0"))))
            parsed["date"] = str(row.get("date", "")).strip()
            parsed["_date_obj"] = date.fromisoformat(parsed["date"]) if parsed["date"] else None

            for metric in BASE_METRICS:
                parsed[metric] = as_float(row.get(metric))

            parsed["days_since_prev_session"] = as_float(row.get("days_since_prev_session"))
            parsed["match_xg_per90"] = as_float(row.get("match_xg_per90"))
            parsed["match_xg_assist_per90"] = as_float(row.get("match_xg_assist_per90"))
            parsed["match_goals_per90"] = as_float(row.get("match_goals_per90"))
            parsed["match_assists_per90"] = as_float(row.get("match_assists_per90"))
            parsed["match_pass_accuracy_pct"] = as_float(row.get("match_pass_accuracy_pct"))
            parsed["match_duel_win_rate_pct"] = as_float(row.get("match_duel_win_rate_pct"))
            rows.append(parsed)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], preferred_start: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    keys = set()
    for row in rows:
        keys.update(row.keys())
    keys.discard("_date_obj")

    ordered: list[str] = []
    for key in preferred_start:
        if key in keys:
            ordered.append(key)
            keys.remove(key)
    ordered.extend(sorted(keys))

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ordered)
        writer.writeheader()
        for row in rows:
            serializable = {k: v for k, v in row.items() if k != "_date_obj"}
            writer.writerow(serializable)


def build_features(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["wy_id"])].append(row)

    output: list[dict[str, object]] = []
    for player_rows in grouped.values():
        player_rows.sort(key=lambda r: (r["_date_obj"], r["date"]))

        metric_history: dict[str, list[float]] = {metric: [] for metric in BASE_METRICS}
        ewma_state: dict[str, float] = {}

        for idx, row in enumerate(player_rows):
            enriched = dict(row)

            for metric in BASE_METRICS:
                values = [as_float(r[metric]) for r in player_rows]
                for window in WINDOWS:
                    section = rolling_slice(values, idx, window)
                    metric_sum = sum(section)
                    metric_mean = mean(section)
                    metric_std = std(section)
                    metric_cv = metric_std / metric_mean if metric_mean else 0.0
                    enriched[f"{metric}_sum_{window}d"] = metric_sum
                    enriched[f"{metric}_mean_{window}d"] = metric_mean
                    enriched[f"{metric}_std_{window}d"] = metric_std
                    enriched[f"{metric}_cv_{window}d"] = metric_cv

            load_mean_7 = as_float(enriched["training_load_proxy_mean_7d"])
            load_std_7 = as_float(enriched["training_load_proxy_std_7d"])
            load_sum_7 = as_float(enriched["training_load_proxy_sum_7d"])
            load_mean_14 = as_float(enriched["training_load_proxy_mean_14d"])
            load_std_14 = as_float(enriched["training_load_proxy_std_14d"])
            load_sum_14 = as_float(enriched["training_load_proxy_sum_14d"])

            enriched["monotony_7d"] = load_mean_7 / load_std_7 if load_std_7 else 0.0
            enriched["strain_7d"] = load_sum_7 * as_float(enriched["monotony_7d"])
            enriched["monotony_14d"] = load_mean_14 / load_std_14 if load_std_14 else 0.0
            enriched["strain_14d"] = load_sum_14 * as_float(enriched["monotony_14d"])

            load_series = [as_float(r["training_load_proxy"]) for r in player_rows]
            current_week = rolling_slice(load_series, idx, 7)
            prev_start = max(0, idx - 13)
            prev_end = max(0, idx - 6)
            previous_week = load_series[prev_start:prev_end]
            current_week_sum = sum(current_week)
            previous_week_sum = sum(previous_week)
            enriched["training_load_week_over_week_delta"] = current_week_sum - previous_week_sum
            enriched["training_load_week_over_week_ratio"] = (
                current_week_sum / previous_week_sum if previous_week_sum else 0.0
            )

            enriched["ac_distance_7_28"] = (
                as_float(enriched["distance_m_mean_7d"]) / as_float(enriched["distance_m_mean_28d"])
                if as_float(enriched["distance_m_mean_28d"])
                else 0.0
            )
            enriched["ac_distance_3_21"] = (
                as_float(enriched["distance_m_mean_3d"]) / as_float(enriched["distance_m_mean_21d"])
                if as_float(enriched["distance_m_mean_21d"])
                else 0.0
            )
            enriched["ac_distance_7_21"] = (
                as_float(enriched["distance_m_mean_7d"]) / as_float(enriched["distance_m_mean_21d"])
                if as_float(enriched["distance_m_mean_21d"])
                else 0.0
            )
            enriched["ac_high_int_7_28"] = (
                as_float(enriched["high_int_acc_abs_m_mean_7d"]) / as_float(enriched["high_int_acc_abs_m_mean_28d"])
                if as_float(enriched["high_int_acc_abs_m_mean_28d"])
                else 0.0
            )
            enriched["ac_high_int_3_21"] = (
                as_float(enriched["high_int_acc_abs_m_mean_3d"])
                / as_float(enriched["high_int_acc_abs_m_mean_21d"])
                if as_float(enriched["high_int_acc_abs_m_mean_21d"])
                else 0.0
            )
            enriched["ac_high_int_7_21"] = (
                as_float(enriched["high_int_acc_abs_m_mean_7d"])
                / as_float(enriched["high_int_acc_abs_m_mean_21d"])
                if as_float(enriched["high_int_acc_abs_m_mean_21d"])
                else 0.0
            )
            enriched["ac_load_7_28"] = (
                as_float(enriched["training_load_proxy_mean_7d"])
                / as_float(enriched["training_load_proxy_mean_28d"])
                if as_float(enriched["training_load_proxy_mean_28d"])
                else 0.0
            )
            enriched["ac_load_3_21"] = (
                as_float(enriched["training_load_proxy_mean_3d"])
                / as_float(enriched["training_load_proxy_mean_21d"])
                if as_float(enriched["training_load_proxy_mean_21d"])
                else 0.0
            )
            enriched["ac_load_7_21"] = (
                as_float(enriched["training_load_proxy_mean_7d"])
                / as_float(enriched["training_load_proxy_mean_21d"])
                if as_float(enriched["training_load_proxy_mean_21d"])
                else 0.0
            )

            for metric in EWMA_METRICS:
                value = as_float(enriched[metric])
                for span in EWMA_SPANS:
                    alpha = 2.0 / (span + 1.0)
                    key = f"{metric}_ewma_{span}d"
                    previous_value = ewma_state.get(key, value)
                    current = alpha * value + (1.0 - alpha) * previous_value
                    ewma_state[key] = current
                    enriched[key] = current

            enriched["ac_distance_ewma_7_28"] = (
                as_float(enriched["distance_m_ewma_7d"]) / as_float(enriched["distance_m_ewma_28d"])
                if as_float(enriched["distance_m_ewma_28d"])
                else 0.0
            )
            enriched["ac_high_int_ewma_7_28"] = (
                as_float(enriched["high_int_acc_abs_m_ewma_7d"]) / as_float(enriched["high_int_acc_abs_m_ewma_28d"])
                if as_float(enriched["high_int_acc_abs_m_ewma_28d"])
                else 0.0
            )
            enriched["ac_load_ewma_7_28"] = (
                as_float(enriched["training_load_proxy_ewma_7d"])
                / as_float(enriched["training_load_proxy_ewma_28d"])
                if as_float(enriched["training_load_proxy_ewma_28d"])
                else 0.0
            )

            for metric in Z_SCORE_METRICS:
                history = metric_history[metric]
                value = as_float(enriched[metric])
                if len(history) >= 5:
                    mu = mean(history)
                    sigma = std(history)
                    z_value = (value - mu) / sigma if sigma else 0.0
                    ratio_vs_baseline = value / mu if mu else 1.0
                else:
                    z_value = 0.0
                    ratio_vs_baseline = 1.0
                enriched[f"{metric}_zscore_player"] = z_value
                enriched[f"{metric}_ratio_vs_baseline"] = ratio_vs_baseline
                history.append(value)

            enriched["recovery_day_flag"] = 1 if as_float(enriched.get("days_since_prev_session")) >= 2 else 0
            output.append(enriched)

    output.sort(key=lambda r: (int(r["wy_id"]), str(r["date"])))
    return output


def build_dictionary_file(path: Path) -> None:
    lines = [
        "# Features Dictionary",
        "",
        "Output: `features/features_v1.csv`",
        "",
        "## Core inputs",
        "- Daily load/device metrics from `data/player_day_features.csv`.",
        "- Player-level match context columns prefixed with `match_`.",
        "",
        "## Rolling features",
        "- For each base metric, generated for windows: 3d, 7d, 14d, 21d, 28d.",
        "- Suffixes:",
        "- `_sum_<wd>` cumulative value over window.",
        "- `_mean_<wd>` arithmetic mean over window.",
        "- `_std_<wd>` population std over window.",
        "- `_cv_<wd>` coefficient of variation (std/mean).",
        "",
        "## Derived training load features",
        "- `monotony_7d`, `monotony_14d` = load mean / load std.",
        "- `strain_7d`, `strain_14d` = load sum * monotony.",
        "- `training_load_week_over_week_delta`, `training_load_week_over_week_ratio`.",
        "",
        "## Acute:Chronic ratios",
        "- `ac_distance_3_21`, `ac_distance_7_21`, `ac_distance_7_28`.",
        "- `ac_high_int_3_21`, `ac_high_int_7_21`, `ac_high_int_7_28`.",
        "- `ac_load_3_21`, `ac_load_7_21`, `ac_load_7_28`.",
        "- EWMA ratios: `ac_distance_ewma_7_28`, `ac_high_int_ewma_7_28`, `ac_load_ewma_7_28`.",
        "",
        "## Smoothing / personalization",
        "- EWMA for selected metrics: `_ewma_7d`, `_ewma_28d`.",
        "- Player personalized z-score: `*_zscore_player` (expanding history, no future leakage).",
        "- Baseline ratio: `*_ratio_vs_baseline`.",
        "",
        "## Notes",
        "- `features_v1` is stored as CSV for portability in current environment.",
        "- Match day flags remain placeholders until explicit match dates are added to source data.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")
    rows = parse_rows(INPUT_FILE)
    features = build_features(rows)
    write_csv(
        OUTPUT_FILE,
        features,
        preferred_start=[
            "date",
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "sessions_count",
            "distance_m",
            "duration_min",
            "distance_per_min",
            "high_speed_share_pct",
            "training_load_proxy",
            "ac_distance_7_28",
            "ac_high_int_7_28",
            "ac_load_7_28",
            "monotony_7d",
            "strain_7d",
        ],
    )
    build_dictionary_file(DICTIONARY_FILE)
    print(f"input rows: {len(rows)}")
    print(f"output rows: {len(features)}")
    print(f"wrote: {OUTPUT_FILE}")
    print(f"wrote: {DICTIONARY_FILE}")


if __name__ == "__main__":
    main()
