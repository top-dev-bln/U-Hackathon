from __future__ import annotations

import csv
import math
import pickle
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, silhouette_score
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "features" / "features_v1.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
REPORT_DIR = PROJECT_ROOT / "reports"
MODELS_DIR = PROJECT_ROOT / "models"
TARGET_DIR = PROJECT_ROOT / "targets"

FORM_OUTPUT_FILE = OUTPUT_DIR / "form_scores_daily.csv"
FATIGUE_OUTPUT_FILE = OUTPUT_DIR / "fatigue_alerts_daily.csv"
AC_DAILY_FILE = OUTPUT_DIR / "ac_ratio_daily.csv"
AC_THRESHOLDS_FILE = OUTPUT_DIR / "player_specific_ac_thresholds.csv"
CLUSTER_FILE = OUTPUT_DIR / "player_clusters.csv"
KPI_DAILY_FILE = OUTPUT_DIR / "player_kpi_daily.csv"
KPI_WEEKLY_FILE = OUTPUT_DIR / "player_kpi_weekly.csv"
TARGETS_FILE = TARGET_DIR / "targets_v1.csv"

BASELINE_REPORT_FILE = REPORT_DIR / "baseline_results.md"
BACKTEST_FILE = REPORT_DIR / "backtest_v1.csv"
FORM_EVAL_REPORT = REPORT_DIR / "form_model_eval.md"
FATIGUE_EVAL_REPORT = REPORT_DIR / "fatigue_model_eval.md"
AC_EVAL_REPORT = REPORT_DIR / "ac_personalization.md"
CLUSTER_BOOK_REPORT = REPORT_DIR / "clustering_profile_book.md"
KPI_DEFINITION_FILE = PROJECT_ROOT / "kpi_definition.md"
TARGET_DEFINITION_FILE = PROJECT_ROOT / "target_definition.md"

FORM_MODEL_7D_FILE = MODELS_DIR / "form_7d.pkl"
FORM_MODEL_14D_FILE = MODELS_DIR / "form_14d.pkl"
FATIGUE_MODEL_FILE = MODELS_DIR / "fatigue_risk.pkl"

DATE_SPLIT = date(2025, 12, 1)

FORM_FEATURES = [
    "distance_per_min_mean_7d",
    "high_speed_share_pct_mean_7d",
    "training_load_proxy_mean_7d",
    "training_load_proxy_cv_7d",
    "ac_distance_7_28",
    "ac_high_int_7_28",
    "ac_load_7_28",
    "ac_distance_3_21",
    "ac_high_int_3_21",
    "ac_load_3_21",
    "ac_distance_ewma_7_28",
    "ac_high_int_ewma_7_28",
    "ac_load_ewma_7_28",
    "monotony_7d",
    "strain_7d",
    "days_since_prev_session",
    "distance_m_zscore_player",
    "high_int_acc_abs_m_zscore_player",
    "training_load_proxy_zscore_player",
    "match_xg_per90",
    "match_xg_assist_per90",
    "match_goals_per90",
    "match_assists_per90",
    "match_pass_accuracy_pct",
    "match_duel_win_rate_pct",
]

FATIGUE_FEATURES = [
    "training_load_proxy",
    "training_load_proxy_mean_7d",
    "training_load_proxy_cv_7d",
    "training_load_week_over_week_ratio",
    "monotony_7d",
    "strain_7d",
    "ac_distance_7_28",
    "ac_high_int_7_28",
    "ac_load_7_28",
    "high_int_acc_abs_m_mean_7d",
    "distance_per_min_mean_7d",
    "days_since_prev_session",
]

PLAYER_PROFILE_FEATURES = [
    "distance_m",
    "distance_per_min",
    "high_speed_share_pct",
    "high_int_acc_abs_m",
    "training_load_proxy",
    "sprints_count_per_min",
    "ac_distance_7_28",
    "ac_high_int_7_28",
    "ac_load_7_28",
    "monotony_7d",
    "strain_7d",
    "match_xg_per90",
    "match_assists_per90",
    "match_duel_win_rate_pct",
]

AC_PRIMARY_FIELDS = ["ac_distance_7_28", "ac_high_int_7_28", "ac_load_7_28"]
AC_BANDED_FIELDS = [
    "ac_distance_3_21",
    "ac_distance_7_21",
    "ac_distance_7_28",
    "ac_distance_ewma_7_28",
    "ac_high_int_3_21",
    "ac_high_int_7_21",
    "ac_high_int_7_28",
    "ac_high_int_ewma_7_28",
    "ac_load_3_21",
    "ac_load_7_21",
    "ac_load_7_28",
    "ac_load_ewma_7_28",
]


@dataclass
class FormModelResult:
    predictions: list[float]
    train_size: int
    test_size: int
    mae_model: float
    rmse_model: float
    r2_model: float
    mae_baseline_current: float
    rmse_baseline_current: float
    mae_baseline_ma14: float
    rmse_baseline_ma14: float
    feature_importance: list[tuple[str, float]]
    model: RandomForestRegressor | None


def as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return default


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    data = sorted(values)
    if q <= 0:
        return data[0]
    if q >= 1:
        return data[-1]
    idx = (len(data) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(data) - 1)
    frac = idx - lo
    return data[lo] * (1 - frac) + data[hi] * frac


def write_csv(path: Path, rows: list[dict[str, object]], preferred_start: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    keys = set()
    for row in rows:
        keys.update(row.keys())
    ordered = []
    for key in preferred_start:
        if key in keys:
            ordered.append(key)
            keys.remove(key)
    ordered.extend(sorted(keys))

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ordered)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            parsed: dict[str, object] = dict(row)
            parsed["wy_id"] = int(float(str(row.get("wy_id", "0"))))
            parsed["date"] = str(row.get("date", "")).strip()
            parsed["_date_obj"] = date.fromisoformat(parsed["date"]) if parsed["date"] else None

            metric_fields = set(FORM_FEATURES + FATIGUE_FEATURES + PLAYER_PROFILE_FEATURES + AC_BANDED_FIELDS)
            metric_fields.update(
                [
                    "distance_per_min",
                    "high_speed_share_pct",
                    "power_metabolic_avg_wkg",
                    "sprints_count_per_min",
                    "training_load_proxy",
                    "distance_m",
                    "high_int_acc_abs_m",
                    "days_since_prev_session",
                ]
            )
            for field in metric_fields:
                parsed[field] = as_float(row.get(field))

            parsed["player_role"] = str(row.get("player_role", "")).strip() or "Unknown"
            parsed["player_short_name"] = str(row.get("player_short_name", "")).strip()
            parsed["player_full_name"] = str(row.get("player_full_name", "")).strip()
            rows.append(parsed)
    rows.sort(key=lambda r: (int(r["wy_id"]), r["_date_obj"], str(r["date"])))
    return rows


def compute_form_proxy(row: dict[str, object]) -> float:
    return (
        0.50 * as_float(row.get("distance_per_min"))
        + 0.25 * as_float(row.get("high_speed_share_pct"))
        + 2.00 * as_float(row.get("power_metabolic_avg_wkg"))
        + 20.0 * as_float(row.get("sprints_count_per_min"))
    )


def build_future_targets_and_baselines(rows: list[dict[str, object]]) -> None:
    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["wy_id"])].append(row)

    for player_rows in grouped.values():
        player_rows.sort(key=lambda r: r["_date_obj"])
        for row in player_rows:
            row["form_proxy_current"] = compute_form_proxy(row)

        for idx, row in enumerate(player_rows):
            current_date = row["_date_obj"]
            if current_date is None:
                row["target_form_proxy_7d"] = ""
                row["target_form_proxy_14d"] = ""
                row["form_baseline_ma14"] = row["form_proxy_current"]
                continue

            past_window = [
                as_float(player_rows[j]["form_proxy_current"])
                for j in range(0, idx + 1)
                if player_rows[j]["_date_obj"] and 0 <= (current_date - player_rows[j]["_date_obj"]).days <= 14
            ]
            row["form_baseline_ma14"] = float(np.mean(past_window)) if past_window else as_float(row["form_proxy_current"])

            future_7: list[float] = []
            future_14: list[float] = []
            for j in range(idx + 1, len(player_rows)):
                other = player_rows[j]
                other_date = other["_date_obj"]
                if other_date is None:
                    continue
                delta = (other_date - current_date).days
                if delta <= 0:
                    continue
                proxy_value = as_float(other["form_proxy_current"])
                if delta <= 7:
                    future_7.append(proxy_value)
                if delta <= 14:
                    future_14.append(proxy_value)
                if delta > 14:
                    break

            row["target_form_proxy_7d"] = float(np.mean(future_7)) if future_7 else ""
            row["target_form_proxy_14d"] = float(np.mean(future_14)) if future_14 else ""


def matrix_from_rows(rows: list[dict[str, object]], columns: list[str]) -> np.ndarray:
    matrix = [[as_float(row.get(column)) for column in columns] for row in rows]
    return np.asarray(matrix, dtype=float)


def train_form_model(rows: list[dict[str, object]], target_key: str) -> FormModelResult:
    eligible = [row for row in rows if row.get(target_key) not in ("", None)]
    if not eligible:
        return FormModelResult([as_float(row.get("form_proxy_current")) for row in rows], 0, 0, 0, 0, 0, 0, 0, 0, 0, [], None)

    train_rows = [row for row in eligible if row["_date_obj"] is not None and row["_date_obj"] < DATE_SPLIT]
    test_rows = [row for row in eligible if row["_date_obj"] is not None and row["_date_obj"] >= DATE_SPLIT]

    if len(train_rows) < 40:
        fallback = [as_float(row.get("form_baseline_ma14")) for row in rows]
        return FormModelResult(fallback, len(train_rows), len(test_rows), 0, 0, 0, 0, 0, 0, 0, [], None)

    x_train = matrix_from_rows(train_rows, FORM_FEATURES)
    y_train = np.asarray([as_float(row[target_key]) for row in train_rows], dtype=float)
    model = RandomForestRegressor(
        n_estimators=400,
        max_depth=8,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    full_predictions = model.predict(matrix_from_rows(rows, FORM_FEATURES))
    importance = sorted(
        list(zip(FORM_FEATURES, [float(x) for x in model.feature_importances_])),
        key=lambda x: x[1],
        reverse=True,
    )

    if test_rows:
        x_test = matrix_from_rows(test_rows, FORM_FEATURES)
        y_test = np.asarray([as_float(row[target_key]) for row in test_rows], dtype=float)
        pred_test = model.predict(x_test)
        baseline_current = np.asarray([as_float(row.get("form_proxy_current")) for row in test_rows], dtype=float)
        baseline_ma14 = np.asarray([as_float(row.get("form_baseline_ma14")) for row in test_rows], dtype=float)

        mae_model = float(mean_absolute_error(y_test, pred_test))
        rmse_model = float(math.sqrt(mean_squared_error(y_test, pred_test)))
        r2_model = float(r2_score(y_test, pred_test))
        mae_baseline_current = float(mean_absolute_error(y_test, baseline_current))
        rmse_baseline_current = float(math.sqrt(mean_squared_error(y_test, baseline_current)))
        mae_baseline_ma14 = float(mean_absolute_error(y_test, baseline_ma14))
        rmse_baseline_ma14 = float(math.sqrt(mean_squared_error(y_test, baseline_ma14)))
    else:
        mae_model = rmse_model = r2_model = 0.0
        mae_baseline_current = rmse_baseline_current = 0.0
        mae_baseline_ma14 = rmse_baseline_ma14 = 0.0

    return FormModelResult(
        predictions=[float(x) for x in full_predictions],
        train_size=len(train_rows),
        test_size=len(test_rows),
        mae_model=mae_model,
        rmse_model=rmse_model,
        r2_model=r2_model,
        mae_baseline_current=mae_baseline_current,
        rmse_baseline_current=rmse_baseline_current,
        mae_baseline_ma14=mae_baseline_ma14,
        rmse_baseline_ma14=rmse_baseline_ma14,
        feature_importance=importance,
        model=model,
    )


def scale_scores_by_role(rows: list[dict[str, object]], value_key: str, output_key: str) -> None:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("player_role", "Unknown"))].append(row)

    for role_rows in grouped.values():
        values = [as_float(row.get(value_key)) for row in role_rows]
        low = min(values) if values else 0.0
        high = max(values) if values else 0.0
        width = high - low
        for row in role_rows:
            value = as_float(row.get(value_key))
            score = 50.0 if width <= 1e-9 else (value - low) / width * 100.0
            row[output_key] = round(max(0.0, min(100.0, score)), 2)


def compute_personalized_bands(rows: list[dict[str, object]], fields: list[str]) -> dict[int, dict[str, float | str]]:
    by_player: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_player[int(row["wy_id"])].append(row)

    global_bands: dict[str, tuple[float, float, float]] = {}
    for field in fields:
        values = [as_float(row.get(field)) for row in rows if as_float(row.get(field)) > 0]
        global_bands[field] = (quantile(values, 0.25), quantile(values, 0.50), quantile(values, 0.75))

    out: dict[int, dict[str, float | str]] = {}
    for player_id, player_rows in by_player.items():
        bands: dict[str, float | str] = {}
        for field in fields:
            values = [as_float(row.get(field)) for row in player_rows if as_float(row.get(field)) > 0]
            if len(values) >= 8:
                low = quantile(values, 0.25)
                med = quantile(values, 0.50)
                high = quantile(values, 0.75)
                source = "personal"
            else:
                low, med, high = global_bands[field]
                source = "global_fallback"
            bands[f"{field}_optimal_low"] = low
            bands[f"{field}_optimal_median"] = med
            bands[f"{field}_optimal_high"] = high
            bands[f"{field}_threshold_source"] = source
        out[player_id] = bands
    return out


def zone_status(value: float, low: float, high: float) -> tuple[str, float]:
    if value <= 0:
        return "insufficient_data", 0.0
    if value < low:
        return "below", (low - value) / low if low else 0.0
    if value > high:
        return "above", (value - high) / high if high else 0.0
    return "optimal", 0.0


def build_ac_daily_rows(
    rows: list[dict[str, object]],
    thresholds: dict[int, dict[str, float | str]],
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        player_id = int(row["wy_id"])
        t = thresholds[player_id]
        per_metric_status: dict[str, str] = {}
        per_metric_excess: dict[str, float] = {}

        for field in AC_PRIMARY_FIELDS:
            value = as_float(row.get(field))
            low = as_float(t[f"{field}_optimal_low"])
            high = as_float(t[f"{field}_optimal_high"])
            status, excess = zone_status(value, low, high)
            per_metric_status[field] = status
            per_metric_excess[field] = excess
            row[f"{field}_status"] = status
            row[f"{field}_excess"] = excess

        excess_values = list(per_metric_excess.values())
        combined_excess = float(np.mean(excess_values)) if excess_values else 0.0
        status_values = list(per_metric_status.values())
        if all(status == "optimal" for status in status_values):
            combined_status = "optimal"
        elif any(status == "above" for status in status_values):
            combined_status = "above_optimal"
        elif any(status == "below" for status in status_values):
            combined_status = "below_optimal"
        else:
            combined_status = "insufficient_data"

        out_row = {
            "date": row["date"],
            "wy_id": player_id,
            "player_short_name": row.get("player_short_name", ""),
            "player_full_name": row.get("player_full_name", ""),
            "player_role": row.get("player_role", ""),
            "ac_distance_7_28": as_float(row.get("ac_distance_7_28")),
            "ac_high_int_7_28": as_float(row.get("ac_high_int_7_28")),
            "ac_load_7_28": as_float(row.get("ac_load_7_28")),
            "ac_distance_status": per_metric_status["ac_distance_7_28"],
            "ac_high_int_status": per_metric_status["ac_high_int_7_28"],
            "ac_load_status": per_metric_status["ac_load_7_28"],
            "ac_combined_status": combined_status,
            "ac_zone_excess": round(combined_excess, 6),
            "ac_threshold_source_distance": t["ac_distance_7_28_threshold_source"],
            "ac_threshold_source_high_int": t["ac_high_int_7_28_threshold_source"],
            "ac_threshold_source_load": t["ac_load_7_28_threshold_source"],
        }
        out.append(out_row)

        row["ac_zone_excess"] = combined_excess
        row["ac_combined_status"] = combined_status
        row["ac_distance_status"] = per_metric_status["ac_distance_7_28"]
        row["ac_high_int_status"] = per_metric_status["ac_high_int_7_28"]
        row["ac_load_status"] = per_metric_status["ac_load_7_28"]
    return out


def normalize_0_1(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    low = float(values.min())
    high = float(values.max())
    width = high - low
    if width <= 1e-9:
        return np.zeros_like(values)
    return (values - low) / width


def build_fatigue_rows(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    x = matrix_from_rows(rows, FATIGUE_FEATURES)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    detector = IsolationForest(n_estimators=250, contamination=0.12, random_state=42)
    detector.fit(x_scaled)
    anomaly = -detector.decision_function(x_scaled)
    anomaly_norm = normalize_0_1(anomaly)

    fatigue_rows: list[dict[str, object]] = []
    for idx, row in enumerate(rows):
        anomaly_score = float(anomaly_norm[idx])
        zone_excess = as_float(row.get("ac_zone_excess"))
        risk_prob = max(0.0, min(1.0, 0.65 * anomaly_score + 0.35 * zone_excess))

        monotony = as_float(row.get("monotony_7d"))
        load_z = as_float(row.get("training_load_proxy_zscore_player"))
        recovery_gap = as_float(row.get("days_since_prev_session"))

        reasons: list[str] = []
        if str(row.get("ac_combined_status")) == "above_optimal":
            reasons.append("ac_above_optimal_zone")
        if monotony >= 2.0:
            reasons.append("high_monotony")
        if load_z >= 1.5:
            reasons.append("load_spike_vs_player_baseline")
        if recovery_gap <= 0:
            reasons.append("consecutive_day_load")
        if not reasons:
            reasons.append("anomaly_pattern_detected")

        if risk_prob >= 0.62:
            risk_level = "high"
        elif risk_prob >= 0.38:
            risk_level = "medium"
        else:
            risk_level = "low"

        static_score = 0
        static_reasons: list[str] = []
        if monotony >= 2.0:
            static_score += 1
            static_reasons.append("monotony>=2.0")
        if as_float(row.get("ac_load_7_28")) >= 1.25:
            static_score += 1
            static_reasons.append("ac_load_7_28>=1.25")
        if as_float(row.get("ac_distance_7_28")) >= 1.25:
            static_score += 1
            static_reasons.append("ac_distance_7_28>=1.25")
        if as_float(row.get("ac_high_int_7_28")) >= 1.25:
            static_score += 1
            static_reasons.append("ac_high_int_7_28>=1.25")
        if recovery_gap <= 0 and load_z >= 1.0:
            static_score += 1
            static_reasons.append("consecutive_day_load_and_spike")

        if static_score >= 2:
            static_level = "high"
        elif static_score == 1:
            static_level = "medium"
        else:
            static_level = "low"

        fatigue_row = {
            "date": row["date"],
            "wy_id": row["wy_id"],
            "player_short_name": row.get("player_short_name", ""),
            "player_full_name": row.get("player_full_name", ""),
            "player_role": row.get("player_role", ""),
            "fatigue_risk_prob": round(risk_prob, 4),
            "fatigue_risk_level": risk_level,
            "overload_flag": 1 if risk_prob >= 0.62 else 0,
            "anomaly_score_norm": round(anomaly_score, 4),
            "ac_zone_excess": round(zone_excess, 4),
            "top_risk_factors": " | ".join(reasons[:3]),
            "static_risk_level": static_level,
            "static_overload_flag": 1 if static_level == "high" else 0,
            "static_risk_reasons": " | ".join(static_reasons) if static_reasons else "none",
        }
        fatigue_rows.append(fatigue_row)
        row["fatigue_risk_prob"] = risk_prob
        row["fatigue_risk_level"] = risk_level
        row["overload_flag"] = fatigue_row["overload_flag"]
        row["static_risk_level"] = static_level
        row["static_overload_flag"] = fatigue_row["static_overload_flag"]

    model_artifact = {
        "detector": detector,
        "scaler": scaler,
        "features": FATIGUE_FEATURES,
        "version": "baseline_v2",
    }
    return fatigue_rows, model_artifact


def build_player_profiles(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["wy_id"])].append(row)

    profiles: list[dict[str, object]] = []
    for player_id, player_rows in grouped.items():
        profile: dict[str, object] = {
            "wy_id": player_id,
            "player_short_name": player_rows[0].get("player_short_name", ""),
            "player_full_name": player_rows[0].get("player_full_name", ""),
            "player_role": player_rows[0].get("player_role", ""),
            "days_count": len(player_rows),
        }
        for feature in PLAYER_PROFILE_FEATURES:
            profile[f"{feature}_avg"] = float(np.mean([as_float(row.get(feature)) for row in player_rows]))
        profiles.append(profile)
    profiles.sort(key=lambda x: int(x["wy_id"]))
    return profiles


def assign_cluster_labels(cluster_rows: list[dict[str, object]], k: int) -> dict[int, str]:
    stats: dict[int, dict[str, float]] = {}
    for cluster_id in range(k):
        subset = [row for row in cluster_rows if int(row["cluster_id"]) == cluster_id]
        if not subset:
            continue
        stats[cluster_id] = {
            "distance": float(np.mean([as_float(r["distance_m_avg"]) for r in subset])),
            "explosive": float(
                np.mean(
                    [
                        as_float(r["high_speed_share_pct_avg"])
                        + as_float(r["high_int_acc_abs_m_avg"]) / 100.0
                        + as_float(r["sprints_count_per_min_avg"]) * 100.0
                        for r in subset
                    ]
                )
            ),
        }

    labels: dict[int, str] = {}
    if not stats:
        return labels
    by_distance = sorted(stats.items(), key=lambda x: x[1]["distance"], reverse=True)
    labels[by_distance[0][0]] = "high-volume runner"
    remaining = [cid for cid in stats.keys() if cid not in labels]
    if remaining:
        explosive_cluster = max(remaining, key=lambda cid: stats[cid]["explosive"])
        labels[explosive_cluster] = "explosive short-burst"
    for cid in stats.keys():
        if cid not in labels:
            labels[cid] = "low-volume high-intensity"
    return labels


def cluster_player_profiles(profiles: list[dict[str, object]]) -> tuple[list[dict[str, object]], float, list[float]]:
    if len(profiles) < 3:
        for row in profiles:
            row["cluster_id"] = 0
            row["cluster_profile"] = "insufficient_population"
            row["pca_1"] = 0.0
            row["pca_2"] = 0.0
        return profiles, 0.0, [0.0, 0.0]

    x = np.asarray(
        [[as_float(row[f"{feature}_avg"]) for feature in PLAYER_PROFILE_FEATURES] for row in profiles],
        dtype=float,
    )
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    pca = PCA(n_components=2)
    pca_values = pca.fit_transform(x_scaled)

    n_clusters = 3 if len(profiles) >= 9 else 2
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=30)
    cluster_ids = model.fit_predict(x_scaled)
    silhouette = float(silhouette_score(x_scaled, cluster_ids)) if n_clusters > 1 else 0.0

    for idx, row in enumerate(profiles):
        row["cluster_id"] = int(cluster_ids[idx])
        row["pca_1"] = float(pca_values[idx, 0])
        row["pca_2"] = float(pca_values[idx, 1])

    labels = assign_cluster_labels(profiles, n_clusters)
    for row in profiles:
        row["cluster_profile"] = labels.get(int(row["cluster_id"]), "balanced hybrid")
    return profiles, silhouette, [float(x) for x in pca.explained_variance_ratio_]


def build_threshold_rows(
    thresholds: dict[int, dict[str, float | str]],
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_player = {int(row["wy_id"]): row for row in rows}
    out: list[dict[str, object]] = []
    for player_id, vals in sorted(thresholds.items()):
        info = by_player.get(player_id, {})
        out.append(
            {
                "wy_id": player_id,
                "player_short_name": info.get("player_short_name", ""),
                "player_full_name": info.get("player_full_name", ""),
                "player_role": info.get("player_role", ""),
                **vals,
            }
        )
    return out


def build_backtest_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        if row["_date_obj"] is None or row["_date_obj"] < DATE_SPLIT:
            continue
        t7 = row.get("target_form_proxy_7d")
        t14 = row.get("target_form_proxy_14d")
        if t7 in ("", None) and t14 in ("", None):
            continue

        pred7 = as_float(row.get("form_model_pred_7d"))
        pred14 = as_float(row.get("form_model_pred_14d"))
        bcur = as_float(row.get("form_proxy_current"))
        bma = as_float(row.get("form_baseline_ma14"))

        out.append(
            {
                "date": row["date"],
                "wy_id": row["wy_id"],
                "player_short_name": row.get("player_short_name", ""),
                "player_role": row.get("player_role", ""),
                "target_form_proxy_7d": t7,
                "target_form_proxy_14d": t14,
                "pred_form_7d": round(pred7, 4),
                "pred_form_14d": round(pred14, 4),
                "baseline_current_proxy": round(bcur, 4),
                "baseline_ma14": round(bma, 4),
                "abs_err_model_7d": round(abs(as_float(t7) - pred7), 4) if t7 not in ("", None) else "",
                "abs_err_model_14d": round(abs(as_float(t14) - pred14), 4) if t14 not in ("", None) else "",
                "abs_err_baseline_current_7d": round(abs(as_float(t7) - bcur), 4) if t7 not in ("", None) else "",
                "abs_err_baseline_current_14d": round(abs(as_float(t14) - bcur), 4) if t14 not in ("", None) else "",
                "abs_err_baseline_ma14_7d": round(abs(as_float(t7) - bma), 4) if t7 not in ("", None) else "",
                "abs_err_baseline_ma14_14d": round(abs(as_float(t14) - bma), 4) if t14 not in ("", None) else "",
            }
        )
    return out


def build_player_kpi_daily(
    rows: list[dict[str, object]],
    profiles: list[dict[str, object]],
) -> list[dict[str, object]]:
    cluster_map = {
        int(row["wy_id"]): {
            "cluster_id": row.get("cluster_id", ""),
            "cluster_profile": row.get("cluster_profile", ""),
            "pca_1": row.get("pca_1", ""),
            "pca_2": row.get("pca_2", ""),
        }
        for row in profiles
    }

    out: list[dict[str, object]] = []
    for row in rows:
        info = cluster_map.get(int(row["wy_id"]), {})
        kpi_row = {
            "date": row["date"],
            "wy_id": row["wy_id"],
            "player_short_name": row.get("player_short_name", ""),
            "player_full_name": row.get("player_full_name", ""),
            "player_role": row.get("player_role", ""),
            "form_score_7d": row.get("form_score_7d", ""),
            "form_score_14d": row.get("form_score_14d", ""),
            "fatigue_risk_prob": round(as_float(row.get("fatigue_risk_prob")), 4),
            "fatigue_risk_level": row.get("fatigue_risk_level", ""),
            "overload_flag": row.get("overload_flag", 0),
            "static_risk_level": row.get("static_risk_level", ""),
            "static_overload_flag": row.get("static_overload_flag", 0),
            "ac_combined_status": row.get("ac_combined_status", ""),
            "ac_zone_excess": round(as_float(row.get("ac_zone_excess")), 4),
            "ac_distance_7_28": round(as_float(row.get("ac_distance_7_28")), 4),
            "ac_high_int_7_28": round(as_float(row.get("ac_high_int_7_28")), 4),
            "ac_load_7_28": round(as_float(row.get("ac_load_7_28")), 4),
            "cluster_id": info.get("cluster_id", ""),
            "cluster_profile": info.get("cluster_profile", ""),
            "cluster_pca_1": info.get("pca_1", ""),
            "cluster_pca_2": info.get("pca_2", ""),
            "training_load_proxy": round(as_float(row.get("training_load_proxy")), 2),
            "distance_m": round(as_float(row.get("distance_m")), 2),
            "distance_per_min": round(as_float(row.get("distance_per_min")), 2),
            "high_int_acc_abs_m": round(as_float(row.get("high_int_acc_abs_m")), 2),
            "underload_candidate": 1
            if row.get("ac_combined_status") == "below_optimal" and row.get("fatigue_risk_level") == "low"
            else 0,
            "overload_candidate": 1
            if int(as_float(row.get("overload_flag"))) == 1 or row.get("ac_combined_status") == "above_optimal"
            else 0,
        }
        out.append(kpi_row)

    by_date: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in out:
        by_date[str(row["date"])].append(row)

    for rows_on_date in by_date.values():
        form_sorted = sorted(rows_on_date, key=lambda x: as_float(x["form_score_7d"]), reverse=True)
        risk_sorted = sorted(rows_on_date, key=lambda x: as_float(x["fatigue_risk_prob"]), reverse=True)
        for rank, row in enumerate(form_sorted, start=1):
            row["rank_form_7d"] = rank
        for rank, row in enumerate(risk_sorted, start=1):
            row["rank_fatigue_risk"] = rank

    out.sort(key=lambda r: (str(r["date"]), int(r["rank_form_7d"])))
    return out


def build_player_kpi_weekly(kpi_daily_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    latest_per_player_week: dict[tuple[int, int, int], dict[str, object]] = {}
    for row in kpi_daily_rows:
        d = date.fromisoformat(str(row["date"]))
        iso = d.isocalendar()
        key = (int(row["wy_id"]), int(iso.year), int(iso.week))
        previous = latest_per_player_week.get(key)
        if previous is None or str(row["date"]) > str(previous["date"]):
            candidate = dict(row)
            candidate["snapshot_year"] = int(iso.year)
            candidate["snapshot_week_iso"] = int(iso.week)
            candidate["output_cadence_days"] = 7
            latest_per_player_week[key] = candidate

    weekly_rows = list(latest_per_player_week.values())
    weekly_rows.sort(key=lambda r: (str(r["date"]), int(r["wy_id"])))

    by_date: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in weekly_rows:
        by_date[str(row["date"])].append(row)
    for rows_on_date in by_date.values():
        form_sorted = sorted(rows_on_date, key=lambda x: as_float(x["form_score_7d"]), reverse=True)
        risk_sorted = sorted(rows_on_date, key=lambda x: as_float(x["fatigue_risk_prob"]), reverse=True)
        for rank, row in enumerate(form_sorted, start=1):
            row["rank_form_7d"] = rank
        for rank, row in enumerate(risk_sorted, start=1):
            row["rank_fatigue_risk"] = rank

    weekly_rows.sort(key=lambda r: (str(r["date"]), int(r["rank_form_7d"])))
    return weekly_rows


def write_form_eval_report(path: Path, result_7d: FormModelResult, result_14d: FormModelResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    top_features_7 = "\n".join([f"- `{name}`: {score:.4f}" for name, score in result_7d.feature_importance[:10]])
    top_features_14 = "\n".join([f"- `{name}`: {score:.4f}" for name, score in result_14d.feature_importance[:10]])
    lines = [
        "# Form Model Eval",
        "",
        "## Horizon 7d",
        f"- Train rows: {result_7d.train_size}",
        f"- Test rows: {result_7d.test_size}",
        f"- MAE model: {result_7d.mae_model:.4f}",
        f"- RMSE model: {result_7d.rmse_model:.4f}",
        f"- R2 model: {result_7d.r2_model:.4f}",
        f"- MAE baseline current proxy: {result_7d.mae_baseline_current:.4f}",
        f"- RMSE baseline current proxy: {result_7d.rmse_baseline_current:.4f}",
        f"- MAE baseline MA14: {result_7d.mae_baseline_ma14:.4f}",
        f"- RMSE baseline MA14: {result_7d.rmse_baseline_ma14:.4f}",
        "",
        "## Horizon 14d",
        f"- Train rows: {result_14d.train_size}",
        f"- Test rows: {result_14d.test_size}",
        f"- MAE model: {result_14d.mae_model:.4f}",
        f"- RMSE model: {result_14d.rmse_model:.4f}",
        f"- R2 model: {result_14d.r2_model:.4f}",
        f"- MAE baseline current proxy: {result_14d.mae_baseline_current:.4f}",
        f"- RMSE baseline current proxy: {result_14d.rmse_baseline_current:.4f}",
        f"- MAE baseline MA14: {result_14d.mae_baseline_ma14:.4f}",
        f"- RMSE baseline MA14: {result_14d.rmse_baseline_ma14:.4f}",
        "",
        "## Top Features 7d",
        top_features_7 if top_features_7 else "- n/a",
        "",
        "## Top Features 14d",
        top_features_14 if top_features_14 else "- n/a",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_fatigue_eval_report(path: Path, fatigue_rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    model_levels = Counter(str(row["fatigue_risk_level"]) for row in fatigue_rows)
    static_levels = Counter(str(row["static_risk_level"]) for row in fatigue_rows)
    model_high = {f"{row['wy_id']}|{row['date']}" for row in fatigue_rows if int(row["overload_flag"]) == 1}
    static_high = {f"{row['wy_id']}|{row['date']}" for row in fatigue_rows if int(row["static_overload_flag"]) == 1}
    overlap = len(model_high & static_high)
    union = len(model_high | static_high)
    jaccard = overlap / union if union else 0.0

    reason_counter = Counter()
    for row in fatigue_rows:
        for token in str(row.get("top_risk_factors", "")).split("|"):
            token = token.strip()
            if token:
                reason_counter[token] += 1

    lines = [
        "# Fatigue Model Eval",
        "",
        f"- Rows: {len(fatigue_rows)}",
        f"- Model level distribution: {dict(model_levels)}",
        f"- Static level distribution: {dict(static_levels)}",
        f"- Model high alerts: {len(model_high)}",
        f"- Static high alerts: {len(static_high)}",
        f"- Alert overlap Jaccard(model vs static): {jaccard:.4f}",
        "",
        "## Top Risk Factors",
    ]
    for name, count in reason_counter.most_common(8):
        lines.append(f"- `{name}`: {count}")
    lines.append("")
    lines.append("Note: risk evaluation is currently unsupervised (no injury/decline labels yet).")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ac_eval_report(
    path: Path,
    ac_rows: list[dict[str, object]],
    threshold_rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status_counts = Counter(str(row["ac_combined_status"]) for row in ac_rows)

    source_counts = Counter()
    for row in threshold_rows:
        for field in AC_PRIMARY_FIELDS:
            source_counts[str(row.get(f"{field}_threshold_source", "unknown"))] += 1

    by_player_above = Counter()
    for row in ac_rows:
        if row["ac_combined_status"] == "above_optimal":
            by_player_above[str(row["player_short_name"])] += 1

    lines = [
        "# AC Personalization Report",
        "",
        f"- Daily rows: {len(ac_rows)}",
        f"- Combined AC status distribution: {dict(status_counts)}",
        f"- Threshold source counts(primary fields): {dict(source_counts)}",
        "",
        "## Top Players Above Optimal Zone",
    ]
    for name, cnt in by_player_above.most_common(10):
        lines.append(f"- `{name}`: {cnt} zile")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_cluster_book(
    path: Path,
    profiles: list[dict[str, object]],
    silhouette: float,
    pca_ratio: list[float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_cluster: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in profiles:
        by_cluster[int(row["cluster_id"])].append(row)

    lines = [
        "# Clustering Profile Book",
        "",
        f"- Players clustered: {len(profiles)}",
        f"- Silhouette: {silhouette:.4f}",
        f"- PCA explained variance: {pca_ratio}",
        "",
    ]

    for cluster_id in sorted(by_cluster.keys()):
        rows = by_cluster[cluster_id]
        label = rows[0].get("cluster_profile", "")
        lines.append(f"## Cluster {cluster_id} - {label}")
        lines.append(f"- Players: {len(rows)}")
        lines.append(f"- Avg distance_m: {np.mean([as_float(r['distance_m_avg']) for r in rows]):.2f}")
        lines.append(f"- Avg distance_per_min: {np.mean([as_float(r['distance_per_min_avg']) for r in rows]):.2f}")
        lines.append(f"- Avg high_speed_share_pct: {np.mean([as_float(r['high_speed_share_pct_avg']) for r in rows]):.2f}")
        lines.append(f"- Avg high_int_acc_abs_m: {np.mean([as_float(r['high_int_acc_abs_m_avg']) for r in rows]):.2f}")
        players = ", ".join(sorted([str(r["player_short_name"]) for r in rows]))
        lines.append(f"- Players list: {players}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_kpi_definition(path: Path) -> None:
    lines = [
        "# KPI Definition",
        "",
        "Source table: `outputs/player_kpi_daily.csv`",
        "Operational weekly table: `outputs/player_kpi_weekly.csv` (cadence 7 days).",
        "",
        "## Core KPIs",
        "- `form_score_7d`, `form_score_14d`: modelled form scores scaled 0-100 by role.",
        "- `fatigue_risk_prob`: model risk probability (0-1).",
        "- `fatigue_risk_level`: low/medium/high from risk probability thresholds.",
        "- `overload_flag`: 1 when fatigue_risk_prob is in high zone.",
        "- `ac_combined_status`: below_optimal / optimal / above_optimal from personalized A:C bands.",
        "- `cluster_profile`: tactical/physical profile cluster label.",
        "",
        "## Operational flags",
        "- `underload_candidate`: below optimal AC with low fatigue risk.",
        "- `overload_candidate`: high risk or AC above optimal zone.",
        "",
        "## Ranking fields",
        "- `rank_form_7d`: descending rank by form score inside same date.",
        "- `rank_fatigue_risk`: descending rank by fatigue risk inside same date.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_target_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        out.append(
            {
                "date": row["date"],
                "wy_id": row["wy_id"],
                "player_short_name": row.get("player_short_name", ""),
                "player_role": row.get("player_role", ""),
                "form_proxy_current": round(as_float(row.get("form_proxy_current")), 4),
                "target_form_proxy_7d": row.get("target_form_proxy_7d", ""),
                "target_form_proxy_14d": row.get("target_form_proxy_14d", ""),
                "fatigue_proxy_binary": 1 if str(row.get("fatigue_risk_level")) == "high" else 0,
                "overload_proxy_binary": 1 if int(as_float(row.get("overload_flag"))) == 1 else 0,
                "ac_combined_status": row.get("ac_combined_status", ""),
            }
        )
    return out


def write_target_definition(path: Path) -> None:
    lines = [
        "# Target Definition (Provisional v1)",
        "",
        "Target dataset: `targets/targets_v1.csv`",
        "",
        "## Form Targets",
        "- `target_form_proxy_7d`: media `form_proxy_current` in urmatoarele 7 zile.",
        "- `target_form_proxy_14d`: media `form_proxy_current` in urmatoarele 14 zile.",
        "- `form_proxy_current` = `0.50*distance_per_min + 0.25*high_speed_share_pct + 2*power_metabolic_avg_wkg + 20*sprints_count_per_min`.",
        "",
        "## Fatigue / Overload Proxy Targets",
        "- `fatigue_proxy_binary`: 1 cand modelul baseline marcheaza nivel `high`.",
        "- `overload_proxy_binary`: 1 cand `overload_flag` este activ.",
        "",
        "## Important",
        "- Aceste target-uri sunt provizorii si trebuie confirmate/calibrate cu staff-ul tehnic.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_baseline_summary(
    path: Path,
    rows: list[dict[str, object]],
    result_7d: FormModelResult,
    result_14d: FormModelResult,
    silhouette: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    train_rows = sum(1 for row in rows if row["_date_obj"] is not None and row["_date_obj"] < DATE_SPLIT)
    test_rows = sum(1 for row in rows if row["_date_obj"] is not None and row["_date_obj"] >= DATE_SPLIT)
    lines = [
        "# Baseline KPI Results",
        "",
        "## Data",
        f"- Input rows: {len(rows)}",
        f"- Train rows (< {DATE_SPLIT.isoformat()}): {train_rows}",
        f"- Test rows (>= {DATE_SPLIT.isoformat()}): {test_rows}",
        "",
        "## Form 7d",
        f"- MAE model: {result_7d.mae_model:.4f}",
        f"- MAE baseline current: {result_7d.mae_baseline_current:.4f}",
        f"- MAE baseline MA14: {result_7d.mae_baseline_ma14:.4f}",
        "",
        "## Form 14d",
        f"- MAE model: {result_14d.mae_model:.4f}",
        f"- MAE baseline current: {result_14d.mae_baseline_current:.4f}",
        f"- MAE baseline MA14: {result_14d.mae_baseline_ma14:.4f}",
        "",
        "## Clustering",
        f"- Silhouette score: {silhouette:.4f}",
        "",
        "## Artifacts",
        "- `reports/backtest_v1.csv`",
        "- `reports/form_model_eval.md`",
        "- `reports/fatigue_model_eval.md`",
        "- `reports/ac_personalization.md`",
        "- `reports/clustering_profile_book.md`",
        "- `outputs/player_kpi_daily.csv`",
        "- `outputs/player_kpi_weekly.csv`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing features file: {INPUT_FILE}")
    rows = parse_rows(INPUT_FILE)
    build_future_targets_and_baselines(rows)

    result_7d = train_form_model(rows, "target_form_proxy_7d")
    result_14d = train_form_model(rows, "target_form_proxy_14d")
    for row, pred7, pred14 in zip(rows, result_7d.predictions, result_14d.predictions):
        row["form_model_pred_7d"] = pred7
        row["form_model_pred_14d"] = pred14

    scale_scores_by_role(rows, "form_model_pred_7d", "form_score_7d")
    scale_scores_by_role(rows, "form_model_pred_14d", "form_score_14d")

    thresholds = compute_personalized_bands(rows, AC_BANDED_FIELDS)
    ac_rows = build_ac_daily_rows(rows, thresholds)
    fatigue_rows, fatigue_model_artifact = build_fatigue_rows(rows)

    profiles = build_player_profiles(rows)
    profiles, silhouette, pca_ratio = cluster_player_profiles(profiles)
    threshold_rows = build_threshold_rows(thresholds, rows)

    form_rows = [
        {
            "date": row["date"],
            "wy_id": row["wy_id"],
            "player_short_name": row.get("player_short_name", ""),
            "player_full_name": row.get("player_full_name", ""),
            "player_role": row.get("player_role", ""),
            "form_proxy_current": round(as_float(row.get("form_proxy_current")), 4),
            "form_baseline_ma14": round(as_float(row.get("form_baseline_ma14")), 4),
            "target_form_proxy_7d": row.get("target_form_proxy_7d", ""),
            "target_form_proxy_14d": row.get("target_form_proxy_14d", ""),
            "form_model_pred_7d": round(as_float(row.get("form_model_pred_7d")), 4),
            "form_model_pred_14d": round(as_float(row.get("form_model_pred_14d")), 4),
            "form_score_7d": row.get("form_score_7d", ""),
            "form_score_14d": row.get("form_score_14d", ""),
            "split": "train" if row["_date_obj"] and row["_date_obj"] < DATE_SPLIT else "test",
        }
        for row in rows
    ]
    backtest_rows = build_backtest_rows(rows)
    kpi_rows = build_player_kpi_daily(rows, profiles)
    kpi_weekly_rows = build_player_kpi_weekly(kpi_rows)
    target_rows = build_target_rows(rows)

    write_csv(
        FORM_OUTPUT_FILE,
        form_rows,
        preferred_start=[
            "date",
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "form_score_7d",
            "form_score_14d",
            "form_model_pred_7d",
            "form_model_pred_14d",
            "form_baseline_ma14",
            "target_form_proxy_7d",
            "target_form_proxy_14d",
            "split",
        ],
    )
    write_csv(
        FATIGUE_OUTPUT_FILE,
        fatigue_rows,
        preferred_start=[
            "date",
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "fatigue_risk_prob",
            "fatigue_risk_level",
            "overload_flag",
            "static_risk_level",
            "static_overload_flag",
            "top_risk_factors",
        ],
    )
    write_csv(
        AC_DAILY_FILE,
        ac_rows,
        preferred_start=[
            "date",
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "ac_distance_7_28",
            "ac_high_int_7_28",
            "ac_load_7_28",
            "ac_combined_status",
            "ac_zone_excess",
        ],
    )
    write_csv(
        AC_THRESHOLDS_FILE,
        threshold_rows,
        preferred_start=[
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "ac_distance_7_28_optimal_low",
            "ac_distance_7_28_optimal_median",
            "ac_distance_7_28_optimal_high",
            "ac_high_int_7_28_optimal_low",
            "ac_high_int_7_28_optimal_median",
            "ac_high_int_7_28_optimal_high",
            "ac_load_7_28_optimal_low",
            "ac_load_7_28_optimal_median",
            "ac_load_7_28_optimal_high",
        ],
    )
    write_csv(
        CLUSTER_FILE,
        profiles,
        preferred_start=[
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "cluster_id",
            "cluster_profile",
            "days_count",
            "pca_1",
            "pca_2",
        ],
    )
    write_csv(
        BACKTEST_FILE,
        backtest_rows,
        preferred_start=[
            "date",
            "wy_id",
            "player_short_name",
            "player_role",
            "target_form_proxy_7d",
            "pred_form_7d",
            "baseline_current_proxy",
            "baseline_ma14",
            "abs_err_model_7d",
            "abs_err_baseline_current_7d",
            "abs_err_baseline_ma14_7d",
            "target_form_proxy_14d",
            "pred_form_14d",
            "abs_err_model_14d",
            "abs_err_baseline_current_14d",
            "abs_err_baseline_ma14_14d",
        ],
    )
    write_csv(
        KPI_DAILY_FILE,
        kpi_rows,
        preferred_start=[
            "date",
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "form_score_7d",
            "form_score_14d",
            "fatigue_risk_prob",
            "fatigue_risk_level",
            "overload_flag",
            "ac_combined_status",
            "ac_zone_excess",
            "cluster_profile",
            "rank_form_7d",
            "rank_fatigue_risk",
            "underload_candidate",
            "overload_candidate",
        ],
    )
    write_csv(
        KPI_WEEKLY_FILE,
        kpi_weekly_rows,
        preferred_start=[
            "date",
            "snapshot_year",
            "snapshot_week_iso",
            "output_cadence_days",
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "form_score_7d",
            "form_score_14d",
            "fatigue_risk_prob",
            "fatigue_risk_level",
            "overload_flag",
            "ac_combined_status",
            "cluster_profile",
            "rank_form_7d",
            "rank_fatigue_risk",
            "underload_candidate",
            "overload_candidate",
        ],
    )
    write_csv(
        TARGETS_FILE,
        target_rows,
        preferred_start=[
            "date",
            "wy_id",
            "player_short_name",
            "player_role",
            "form_proxy_current",
            "target_form_proxy_7d",
            "target_form_proxy_14d",
            "fatigue_proxy_binary",
            "overload_proxy_binary",
            "ac_combined_status",
        ],
    )

    write_form_eval_report(FORM_EVAL_REPORT, result_7d, result_14d)
    write_fatigue_eval_report(FATIGUE_EVAL_REPORT, fatigue_rows)
    write_ac_eval_report(AC_EVAL_REPORT, ac_rows, threshold_rows)
    write_cluster_book(CLUSTER_BOOK_REPORT, profiles, silhouette, pca_ratio)
    write_kpi_definition(KPI_DEFINITION_FILE)
    write_target_definition(TARGET_DEFINITION_FILE)
    write_baseline_summary(BASELINE_REPORT_FILE, rows, result_7d, result_14d, silhouette)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if result_7d.model is not None:
        with FORM_MODEL_7D_FILE.open("wb") as handle:
            pickle.dump({"model": result_7d.model, "features": FORM_FEATURES, "horizon": "7d"}, handle)
    if result_14d.model is not None:
        with FORM_MODEL_14D_FILE.open("wb") as handle:
            pickle.dump({"model": result_14d.model, "features": FORM_FEATURES, "horizon": "14d"}, handle)
    with FATIGUE_MODEL_FILE.open("wb") as handle:
        pickle.dump(fatigue_model_artifact, handle)

    print(f"rows processed: {len(rows)}")
    print(f"form train/test 7d: {result_7d.train_size}/{result_7d.test_size}")
    print(f"form train/test 14d: {result_14d.train_size}/{result_14d.test_size}")
    print(f"silhouette: {silhouette:.4f}")
    print(f"wrote: {FORM_OUTPUT_FILE}")
    print(f"wrote: {FATIGUE_OUTPUT_FILE}")
    print(f"wrote: {AC_DAILY_FILE}")
    print(f"wrote: {AC_THRESHOLDS_FILE}")
    print(f"wrote: {CLUSTER_FILE}")
    print(f"wrote: {KPI_DAILY_FILE}")
    print(f"wrote: {KPI_WEEKLY_FILE}")
    print(f"wrote: {TARGETS_FILE}")
    print(f"wrote: {BACKTEST_FILE}")
    print(f"wrote: {BASELINE_REPORT_FILE}")
    print(f"wrote: {FORM_EVAL_REPORT}")
    print(f"wrote: {FATIGUE_EVAL_REPORT}")
    print(f"wrote: {AC_EVAL_REPORT}")
    print(f"wrote: {CLUSTER_BOOK_REPORT}")
    print(f"wrote: {KPI_DEFINITION_FILE}")
    print(f"wrote: {TARGET_DEFINITION_FILE}")
    print(f"wrote: {FORM_MODEL_7D_FILE}")
    print(f"wrote: {FORM_MODEL_14D_FILE}")
    print(f"wrote: {FATIGUE_MODEL_FILE}")


if __name__ == "__main__":
    main()
