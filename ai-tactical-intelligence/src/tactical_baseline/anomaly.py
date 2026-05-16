from __future__ import annotations

import csv
import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sklearn.ensemble import IsolationForest

ANOMALY_FEATURES: tuple[str, ...] = (
    "passSuccessRate",
    "progressivePassSuccessRate",
    "finalThirdPassSuccessRate",
    "lossRate",
    "ownHalfLossRate",
    "dangerousLossRate",
    "shotOnTargetRate",
    "xgPerShot",
    "boxEfficiency",
    "counterpressingRate",
    "highRecoveryRate",
    "duelSuccessRate",
)


@dataclass
class AnomalyDetectionResult:
    rows: list[dict[str, Any]]
    fieldnames: list[str]
    report_payload: dict[str, Any]


def build_anomaly_scores(
    team_feature_rows: list[dict[str, Any]],
    *,
    u_cluj_aliases: list[str],
    team_assignment_mode: str,
    contamination: float,
    random_state: int,
    n_estimators: int,
) -> AnomalyDetectionResult:
    normalized_aliases = {_normalize_team_name(alias) for alias in u_cluj_aliases}

    x_matrix: list[list[float]] = []
    meta_rows: list[dict[str, Any]] = []
    for row in team_feature_rows:
        feature_vector = [_safe_feature_value(row.get(feature)) for feature in ANOMALY_FEATURES]
        x_matrix.append(feature_vector)
        meta_rows.append(row)

    if len(x_matrix) < 2:
        report_payload = {
            "scope": {
                "team_assignment_mode": team_assignment_mode,
                "feature_count": len(ANOMALY_FEATURES),
                "rows_used": len(x_matrix),
            },
            "model": {
                "name": "IsolationForest",
                "contamination": contamination,
                "random_state": random_state,
                "n_estimators": n_estimators,
            },
            "warnings": ["Not enough rows to fit IsolationForest."],
            "totals": {
                "rows_scored": 0,
                "u_cluj_rows_scored": 0,
                "u_cluj_anomalous_rows": 0,
            },
        }
        return AnomalyDetectionResult(rows=[], fieldnames=_output_fieldnames(), report_payload=report_payload)

    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=n_estimators,
    )
    model.fit(x_matrix)

    raw_scores = model.score_samples(x_matrix)
    decision_scores = model.decision_function(x_matrix)
    predictions = model.predict(x_matrix)

    raw_min = float(min(raw_scores))
    raw_max = float(max(raw_scores))
    raw_range = raw_max - raw_min

    output_rows: list[dict[str, Any]] = []
    u_cluj_rows_scored = 0
    u_cluj_anomalous_rows = 0

    for idx, row in enumerate(meta_rows):
        team_name = _as_text(row.get("team_name")) or ""
        is_u_cluj = _normalize_team_name(team_name) in normalized_aliases
        if is_u_cluj:
            u_cluj_rows_scored += 1

        raw_score = float(raw_scores[idx])
        decision_score = float(decision_scores[idx])
        pred = int(predictions[idx])
        is_anomalous = pred == -1
        if is_u_cluj and is_anomalous:
            u_cluj_anomalous_rows += 1

        anomaly_score = 0.0 if raw_range == 0 else (raw_max - raw_score) / raw_range
        anomaly_score = _clamp(anomaly_score, 0.0, 1.0)

        out = {
            "match_id": _to_int(row.get("match_id")),
            "team_id": _to_int(row.get("team_id")),
            "team_name": team_name,
            "is_u_cluj": int(is_u_cluj),
            "anomalyScore": anomaly_score,
            "isAnomalous": int(is_anomalous),
            "isolation_raw_score": raw_score,
            "isolation_decision_score": decision_score,
        }
        for feature in ANOMALY_FEATURES:
            out[feature] = _safe_feature_value(row.get(feature))
        output_rows.append(out)

    report_payload = {
        "scope": {
            "team_assignment_mode": team_assignment_mode,
            "feature_count": len(ANOMALY_FEATURES),
            "rows_used": len(x_matrix),
        },
        "model": {
            "name": "IsolationForest",
            "contamination": contamination,
            "random_state": random_state,
            "n_estimators": n_estimators,
            "features": list(ANOMALY_FEATURES),
        },
        "score_normalization": {
            "raw_score_min": raw_min,
            "raw_score_max": raw_max,
            "raw_score_range": raw_range,
            "anomaly_score_formula": "anomalyScore = (raw_max - raw_score) / (raw_max - raw_min)",
        },
        "totals": {
            "rows_scored": len(output_rows),
            "anomalous_rows": sum(1 for row in output_rows if row["isAnomalous"] == 1),
            "u_cluj_rows_scored": u_cluj_rows_scored,
            "u_cluj_anomalous_rows": u_cluj_anomalous_rows,
        },
        "u_cluj_samples": [
            {
                "match_id": row["match_id"],
                "team_id": row["team_id"],
                "anomalyScore": row["anomalyScore"],
                "isAnomalous": row["isAnomalous"],
            }
            for row in output_rows
            if row["is_u_cluj"] == 1
        ],
    }

    return AnomalyDetectionResult(
        rows=output_rows,
        fieldnames=_output_fieldnames(),
        report_payload=report_payload,
    )


def write_anomaly_scores_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _serialize_csv_value(row.get(field)) for field in fieldnames})


def _output_fieldnames() -> list[str]:
    return [
        "match_id",
        "team_id",
        "team_name",
        "is_u_cluj",
        "anomalyScore",
        "isAnomalous",
        "isolation_raw_score",
        "isolation_decision_score",
        *ANOMALY_FEATURES,
    ]


def _normalize_team_name(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(without_marks.lower().strip().split())


def _safe_feature_value(value: Any) -> float:
    parsed = _to_float_or_none(value)
    if parsed is None or not math.isfinite(parsed):
        return 0.0
    return parsed


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            try:
                return int(stripped)
            except ValueError:
                return None
    return None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _serialize_csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value
