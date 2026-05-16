from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FinalReportResult:
    payload: dict[str, Any]


def build_u_cluj_final_report(
    comparisons_payload: dict[str, Any],
    insights_payload: dict[str, Any],
    anomaly_rows: list[dict[str, Any]],
    tactical_clusters_payload: dict[str, Any],
    *,
    team_assignment_mode: str,
) -> FinalReportResult:
    comparisons_index = _index_by_match_team(comparisons_payload.get("matches", []), "matchId", "teamId")
    insights_index = _index_by_match_team(insights_payload.get("matches", []), "matchId", "teamId")
    anomaly_index = _index_by_match_team(anomaly_rows, "match_id", "team_id")
    cluster_index = _index_by_match_team(tactical_clusters_payload.get("matches", []), "matchId", "teamId")

    output_matches: list[dict[str, Any]] = []
    for key in sorted(comparisons_index):
        comp = comparisons_index[key]
        insight_row = insights_index.get(key, {})
        anomaly_row = anomaly_index.get(key, {})
        cluster_row = cluster_index.get(key, {})

        comparisons = comp.get("comparisons", {})
        insights = insight_row.get("insights", [])
        weakness_breakdown = _build_weakness_breakdown(insights, comparisons)
        max_insight_severity = _max_insight_severity(insights)
        overall_score = _compute_overall_weakness_score(weakness_breakdown, max_insight_severity)
        risk_level = _risk_level(overall_score)

        metrics = {}
        for metric_name, metric_obj in comparisons.items():
            if isinstance(metric_obj, dict):
                metrics[metric_name] = _round4(_to_float(metric_obj.get("value")))

        anomaly_score = _round4(_to_float(anomaly_row.get("anomalyScore")))
        is_anomalous = bool(_to_int(anomaly_row.get("isAnomalous")) == 1)

        output_matches.append(
            {
                "matchId": _to_int(comp.get("matchId")),
                "teamId": _to_int(comp.get("teamId")),
                "teamName": comp.get("teamName"),
                "homeTeamName": comp.get("homeTeamName"),
                "awayTeamName": comp.get("awayTeamName"),
                "isHomeTeam": _to_int(comp.get("isHomeTeam")),
                "baselineScope": "Superliga - all available matches",
                "overallWeaknessScore": _round4(overall_score),
                "riskLevel": risk_level,
                "weaknessBreakdown": weakness_breakdown,
                "tacticalProfile": cluster_row.get("tacticalProfile", "unknown_profile"),
                "clusterId": _to_int(cluster_row.get("clusterId")),
                "clusterExplanation": cluster_row.get("clusterExplanation", []),
                "anomalyScore": anomaly_score,
                "isAnomalous": is_anomalous,
                "metrics": metrics,
                "comparisons": comparisons,
                "insights": insights,
            }
        )

    payload = {
        "scope": {
            "team_assignment_mode": team_assignment_mode,
            "matches_count": len(output_matches),
            "baseline_scope": "Superliga - all available matches",
        },
        "matches": output_matches,
    }
    return FinalReportResult(payload=payload)


def _build_weakness_breakdown(insights: list[dict[str, Any]], comparisons: dict[str, Any]) -> dict[str, float]:
    by_type = {
        "buildUpWeaknessScore": 0.0,
        "ballLossWeaknessScore": 0.0,
        "finalThirdWeaknessScore": 0.0,
        "pressingWeaknessScore": 0.0,
        "duelWeaknessScore": 0.0,
    }
    type_to_bucket = {
        "build_up": "buildUpWeaknessScore",
        "ball_loss": "ballLossWeaknessScore",
        "final_third": "finalThirdWeaknessScore",
        "pressing": "pressingWeaknessScore",
        "duels": "duelWeaknessScore",
    }
    for insight in insights:
        if not isinstance(insight, dict):
            continue
        insight_type = insight.get("type")
        bucket = type_to_bucket.get(insight_type)
        if bucket is None:
            continue
        score = _clamp(_to_float(insight.get("severityScore")), 0.0, 1.0)
        by_type[bucket] = max(by_type[bucket], score)

    # Fallback from metric-level comparisons so a weak status is visible even
    # when no explicit rule-based insight was generated for that category.
    metric_bucket_map = {
        "buildUpWeaknessScore": (
            "passSuccessRate",
            "progressivePassSuccessRate",
            "finalThirdPassSuccessRate",
            "progressivePassShare",
            "finalThirdEntryShare",
        ),
        "ballLossWeaknessScore": ("lossRate", "ownHalfLossRate", "dangerousLossRate"),
        "finalThirdWeaknessScore": ("shotOnTargetRate", "xgPerShot", "boxEfficiency"),
        "pressingWeaknessScore": ("counterpressingRate", "highRecoveryRate", "pressingDuelSuccessRate"),
        "duelWeaknessScore": (
            "duelSuccessRate",
            "defensiveDuelSuccessRate",
            "offensiveDuelSuccessRate",
            "aerialDuelSuccessRate",
        ),
    }
    for bucket, metric_names in metric_bucket_map.items():
        for metric_name in metric_names:
            comp = comparisons.get(metric_name)
            if not isinstance(comp, dict):
                continue
            by_type[bucket] = max(by_type[bucket], _comparison_weakness_score(comp))

    return {k: _round4(v) for k, v in by_type.items()}


def _comparison_weakness_score(comp: dict[str, Any]) -> float:
    status = _as_text(comp.get("status")) or ""
    if status == "very_weak":
        return 0.40
    if status == "weak":
        return 0.22
    if status == "warning":
        return 0.16
    return 0.0


def _compute_overall_weakness_score(breakdown: dict[str, float], max_insight_severity: float) -> float:
    weighted_score = _clamp(
        0.30 * _to_float(breakdown.get("buildUpWeaknessScore"))
        + 0.25 * _to_float(breakdown.get("ballLossWeaknessScore"))
        + 0.20 * _to_float(breakdown.get("finalThirdWeaknessScore"))
        + 0.15 * _to_float(breakdown.get("pressingWeaknessScore"))
        + 0.10 * _to_float(breakdown.get("duelWeaknessScore")),
        0.0,
        1.0,
    )
    severity_floor = _clamp(_to_float(max_insight_severity) * 0.75, 0.0, 1.0)
    return max(weighted_score, severity_floor)


def _max_insight_severity(insights: list[dict[str, Any]]) -> float:
    max_score = 0.0
    for insight in insights:
        if not isinstance(insight, dict):
            continue
        score = _clamp(_to_float(insight.get("severityScore")), 0.0, 1.0)
        if score > max_score:
            max_score = score
    return max_score


def _risk_level(score: float) -> str:
    if score < 0.20:
        return "low"
    if score < 0.40:
        return "medium-low"
    if score < 0.60:
        return "medium"
    if score < 0.80:
        return "medium-high"
    return "high"


def _index_by_match_team(
    rows: list[dict[str, Any]],
    match_key: str,
    team_key: str,
) -> dict[tuple[int | None, int | None], dict[str, Any]]:
    index: dict[tuple[int | None, int | None], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        mk = _to_int(row.get(match_key))
        tk = _to_int(row.get(team_key))
        index[(mk, tk)] = row
    return index


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


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return 0.0
        try:
            return float(stripped)
        except ValueError:
            return 0.0
    return 0.0


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _round4(value: float) -> float:
    return round(value, 4)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
