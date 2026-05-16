from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class LeagueBaselineResult:
    baseline_payload: dict[str, Any]
    distributions_payload: dict[str, Any]


def build_league_baseline(
    feature_rows: list[dict[str, Any]],
    metric_names: list[str],
    *,
    team_assignment_mode: str,
) -> LeagueBaselineResult:
    metrics_baseline: dict[str, dict[str, float | int | None]] = {}
    metrics_distributions: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    for metric in metric_names:
        values = [_to_float_or_none(row.get(metric)) for row in feature_rows]
        clean_values = [value for value in values if value is not None and math.isfinite(value)]

        if not clean_values:
            warnings.append(f"No valid values found for metric '{metric}'.")
            metrics_baseline[metric] = {
                "count": 0,
                "mean": None,
                "std": None,
                "min": None,
                "max": None,
                "p10": None,
                "p25": None,
                "p50": None,
                "p75": None,
                "p90": None,
            }
            metrics_distributions[metric] = {
                "count": 0,
                "values_sorted": [],
            }
            continue

        clean_values.sort()
        count = len(clean_values)
        mean_value = sum(clean_values) / count
        std_value = _population_std(clean_values, mean_value)

        metrics_baseline[metric] = {
            "count": count,
            "mean": mean_value,
            "std": std_value,
            "min": clean_values[0],
            "max": clean_values[-1],
            "p10": _percentile(clean_values, 10.0),
            "p25": _percentile(clean_values, 25.0),
            "p50": _percentile(clean_values, 50.0),
            "p75": _percentile(clean_values, 75.0),
            "p90": _percentile(clean_values, 90.0),
        }
        metrics_distributions[metric] = {
            "count": count,
            "values_sorted": clean_values,
        }

    baseline_payload: dict[str, Any] = {
        "scope": {
            "team_assignment_mode": team_assignment_mode,
            "team_match_rows_used": len(feature_rows),
            "metrics_count": len(metric_names),
        },
        "metrics": metrics_baseline,
    }
    if warnings:
        baseline_payload["warnings"] = warnings

    distributions_payload: dict[str, Any] = {
        "scope": {
            "team_assignment_mode": team_assignment_mode,
            "team_match_rows_used": len(feature_rows),
            "metrics_count": len(metric_names),
        },
        "metrics": metrics_distributions,
    }
    if warnings:
        distributions_payload["warnings"] = warnings

    return LeagueBaselineResult(
        baseline_payload=baseline_payload,
        distributions_payload=distributions_payload,
    )


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


def _population_std(values: list[float], mean_value: float) -> float:
    if not values:
        return 0.0
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if percentile <= 0:
        return sorted_values[0]
    if percentile >= 100:
        return sorted_values[-1]

    rank = (len(sorted_values) - 1) * (percentile / 100.0)
    lower_idx = int(math.floor(rank))
    upper_idx = int(math.ceil(rank))
    if lower_idx == upper_idx:
        return sorted_values[lower_idx]
    weight = rank - lower_idx
    return sorted_values[lower_idx] * (1.0 - weight) + sorted_values[upper_idx] * weight
