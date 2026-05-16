from __future__ import annotations

import bisect
import math
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass
class UClujComparisonsResult:
    comparisons_payload: dict[str, Any]


def build_u_cluj_comparisons(
    team_feature_rows: list[dict[str, Any]],
    league_baseline_payload: dict[str, Any],
    league_distributions_payload: dict[str, Any],
    metric_directions: dict[str, str],
    u_cluj_aliases: list[str],
    *,
    team_assignment_mode: str,
) -> UClujComparisonsResult:
    alias_normalized = {_normalize_name(alias) for alias in u_cluj_aliases}
    selected_rows = [
        row
        for row in team_feature_rows
        if _normalize_name(_as_text(row.get("team_name"))) in alias_normalized
    ]
    selected_rows.sort(key=lambda row: _as_int(row.get("match_id")) or 0)

    baseline_metrics = league_baseline_payload.get("metrics", {})
    distributions_metrics = league_distributions_payload.get("metrics", {})

    output_matches: list[dict[str, Any]] = []
    for row in selected_rows:
        match_id = _as_int(row.get("match_id"))
        team_id = _as_int(row.get("team_id"))
        team_name = _as_text(row.get("team_name")) or ""
        home_team_name = _as_text(row.get("home_team_name"))
        away_team_name = _as_text(row.get("away_team_name"))
        is_home_team = _as_int(row.get("is_home_team"))

        metric_comparisons: dict[str, Any] = {}
        weak_metrics_count = 0

        for metric_name, direction in metric_directions.items():
            metric_value = _to_float(row.get(metric_name))
            baseline_stats = baseline_metrics.get(metric_name, {})
            league_mean = _to_float_or_none(baseline_stats.get("mean"))
            league_std = _to_float_or_none(baseline_stats.get("std"))
            distribution = distributions_metrics.get(metric_name, {})
            values_sorted = _to_float_list(distribution.get("values_sorted", []))

            if league_mean is None or league_std is None or league_std == 0:
                z_score = None
                percentile = None
                status = "insufficient_data"
                is_weakness = False
            else:
                z_score = _z_score(metric_value, league_mean, league_std)
                percentile = _percentile_rank(metric_value, values_sorted)
                status = _status_from_z_score(z_score, direction)
                status = _apply_warning_band(status=status, percentile=percentile, direction=direction)
                is_weakness = _is_weakness(status)
            if is_weakness:
                weak_metrics_count += 1

            metric_comparisons[metric_name] = {
                "value": metric_value,
                "leagueAverage": league_mean,
                "leagueStd": league_std,
                "zScore": z_score,
                "percentile": percentile,
                "direction": direction,
                "status": status,
                "isWeakness": is_weakness,
            }

        output_matches.append(
            {
                "matchId": match_id,
                "teamId": team_id,
                "teamName": team_name,
                "homeTeamName": home_team_name,
                "awayTeamName": away_team_name,
                "isHomeTeam": is_home_team,
                "weakMetricsCount": weak_metrics_count,
                "metricsCompared": len(metric_directions),
                "comparisons": metric_comparisons,
            }
        )

    payload = {
        "scope": {
            "team_assignment_mode": team_assignment_mode,
            "team_aliases_used": u_cluj_aliases,
            "metric_count": len(metric_directions),
            "u_cluj_match_count": len(output_matches),
        },
        "matches": output_matches,
    }
    return UClujComparisonsResult(comparisons_payload=payload)


def _normalize_name(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(without_diacritics.lower().strip().split())


def _status_from_z_score(z_score: float | None, direction: str) -> str:
    if z_score is None:
        return "no_baseline"

    if direction == "higher_is_better":
        if z_score <= -1.5:
            return "very_weak"
        if z_score <= -0.75:
            return "weak"
        if z_score < 0.75:
            return "normal"
        if z_score < 1.5:
            return "strong"
        return "very_strong"

    if direction == "higher_is_worse":
        if z_score <= -1.5:
            return "very_strong"
        if z_score <= -0.75:
            return "strong"
        if z_score < 0.75:
            return "normal"
        if z_score < 1.5:
            return "weak"
        return "very_weak"

    return "unknown_direction"


def _is_weakness(status: str) -> bool:
    return status in {"weak", "very_weak"}


def _apply_warning_band(*, status: str, percentile: float | None, direction: str) -> str:
    if percentile is None:
        return status
    if status != "normal":
        return status
    if direction == "higher_is_worse" and percentile >= 75.0:
        return "warning"
    if direction == "higher_is_better" and percentile <= 25.0:
        return "warning"
    return status


def _z_score(value: float, mean: float | None, std: float | None) -> float | None:
    if mean is None or std is None or std == 0:
        return None
    return (value - mean) / std


def _percentile_rank(value: float, values_sorted: list[float]) -> float | None:
    if not values_sorted:
        return None
    position = bisect.bisect_right(values_sorted, value)
    return (position / len(values_sorted)) * 100.0


def _to_float_list(values: list[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        parsed = _to_float_or_none(value)
        if parsed is not None and math.isfinite(parsed):
            out.append(parsed)
    return out


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    return None


def _as_int(value: Any) -> int | None:
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


def _to_float(value: Any) -> float:
    parsed = _to_float_or_none(value)
    return parsed if parsed is not None else 0.0


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
