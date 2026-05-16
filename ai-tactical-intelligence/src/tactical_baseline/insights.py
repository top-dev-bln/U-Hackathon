from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class UClujInsightsResult:
    report_payload: dict[str, Any]


def build_u_cluj_tactical_weakness_report(
    comparisons_payload: dict[str, Any],
    team_feature_rows: list[dict[str, Any]],
    *,
    max_insights_per_match: int = 6,
    team_assignment_mode: str,
) -> UClujInsightsResult:
    team_row_index = _index_team_rows(team_feature_rows)
    match_reports: list[dict[str, Any]] = []

    for match in comparisons_payload.get("matches", []):
        match_id = _to_int(match.get("matchId"))
        team_id = _to_int(match.get("teamId"))
        comparisons = match.get("comparisons", {})
        team_row = team_row_index.get((match_id, team_id), {})

        insights = _generate_insights_for_match(comparisons, team_row)
        insights.sort(key=lambda item: item["severityScore"], reverse=True)
        insights = insights[: max(max_insights_per_match, 1)]

        match_reports.append(
            {
                "matchId": match_id,
                "teamId": team_id,
                "teamName": match.get("teamName"),
                "homeTeamName": match.get("homeTeamName"),
                "awayTeamName": match.get("awayTeamName"),
                "isHomeTeam": match.get("isHomeTeam"),
                "insightCount": len(insights),
                "insights": insights,
            }
        )

    payload = {
        "scope": {
            "team_assignment_mode": team_assignment_mode,
            "max_insights_per_match": max(max_insights_per_match, 1),
            "matches_analyzed": len(match_reports),
        },
        "matches": match_reports,
    }
    return UClujInsightsResult(report_payload=payload)


def _generate_insights_for_match(comparisons: dict[str, Any], team_row: dict[str, Any]) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    def comp(metric: str) -> dict[str, Any]:
        value = comparisons.get(metric)
        return value if isinstance(value, dict) else {}

    def add_insight(
        *,
        insight_type: str,
        title: str,
        message: str,
        recommendation: str,
        severity_score: float,
        evidence: dict[str, Any],
    ) -> None:
        if title in seen_titles:
            return
        seen_titles.add(title)
        score = _clamp(severity_score, 0.0, 1.0)
        insights.append(
            {
                "type": insight_type,
                "severity": _severity_label(score),
                "severityScore": score,
                "confidence": _clamp(0.55 + 0.45 * score, 0.0, 1.0),
                "title": title,
                "message": message,
                "evidence": evidence,
                "recommendation": recommendation,
            }
        )

    # Build-up rules
    progressive_pass = comp("progressivePassSuccessRate")
    z = _to_float_or_none(progressive_pass.get("zScore"))
    if z is not None and z < -1.0:
        add_insight(
            insight_type="build_up",
            title="Low progressive pass success",
            message="Progressive passing efficiency is below league baseline.",
            recommendation="Improve central progression patterns and third-man passing options.",
            severity_score=_z_based_weakness_score(z, threshold=-1.0),
            evidence=_metric_evidence("progressivePassSuccessRate", progressive_pass),
        )

    final_third_pass = comp("finalThirdPassSuccessRate")
    z = _to_float_or_none(final_third_pass.get("zScore"))
    if z is not None and z < -1.0:
        add_insight(
            insight_type="build_up",
            title="Low success entering final third",
            message="Final-third entry passing success is below league baseline.",
            recommendation="Increase quality of vertical support angles and timing before final-third entry.",
            severity_score=_z_based_weakness_score(z, threshold=-1.0),
            evidence=_metric_evidence("finalThirdPassSuccessRate", final_third_pass),
        )

    progressive_share = comp("progressivePassShare")
    percentile = _to_float_or_none(progressive_share.get("percentile"))
    if percentile is not None and percentile < 25.0:
        add_insight(
            insight_type="build_up",
            title="Low vertical progression share",
            message="The share of progressive passes is in the bottom quartile.",
            recommendation="Increase vertical passing volume from midfield and first build-up line.",
            severity_score=_percentile_low_score(percentile, threshold=25.0),
            evidence=_metric_evidence("progressivePassShare", progressive_share),
        )

    # Ball-loss rules
    loss_rate = comp("lossRate")
    percentile = _to_float_or_none(loss_rate.get("percentile"))
    if percentile is not None and percentile > 75.0:
        add_insight(
            insight_type="ball_loss",
            title="High ball losses",
            message="Ball-loss rate is in the risk zone versus league baseline.",
            recommendation="Reduce forced actions in congested zones and improve support distances.",
            severity_score=_percentile_high_score(percentile, threshold=75.0),
            evidence=_metric_evidence("lossRate", loss_rate),
        )

    own_half_loss = comp("ownHalfLossRate")
    percentile = _to_float_or_none(own_half_loss.get("percentile"))
    if percentile is not None and percentile > 75.0:
        add_insight(
            insight_type="ball_loss",
            title="Risky losses in own half",
            message="Own-half loss rate is above safe league ranges.",
            recommendation="Prioritize safer first-phase exits and cleaner support under pressure.",
            severity_score=_percentile_high_score(percentile, threshold=75.0),
            evidence=_metric_evidence("ownHalfLossRate", own_half_loss),
        )

    dangerous_loss = comp("dangerousLossRate")
    dangerous_count = _to_float_or_none(team_row.get("total_dangerousOwnHalfLosses")) or 0.0
    dangerous_value = _to_float_or_none(dangerous_loss.get("value"))
    dangerous_avg = _to_float_or_none(dangerous_loss.get("leagueAverage"))
    if dangerous_count > 0 and dangerous_value is not None and dangerous_avg is not None and dangerous_value > dangerous_avg:
        score_from_gap = 0.0 if dangerous_avg <= 0 else min(1.0, (dangerous_value - dangerous_avg) / dangerous_avg)
        score_from_count = min(1.0, dangerous_count / 3.0)
        add_insight(
            insight_type="ball_loss",
            title="Dangerous own-half losses",
            message="Dangerous loss exposure in own half is above league norm.",
            recommendation="Protect central rest-defense zones and reduce risky receptions facing own goal.",
            severity_score=0.5 * score_from_gap + 0.5 * score_from_count,
            evidence={
                **_metric_evidence("dangerousLossRate", dangerous_loss),
                "dangerousOwnHalfLosses": dangerous_count,
            },
        )

    # Final third rules
    xg_per_shot = comp("xgPerShot")
    xg_z = _to_float_or_none(xg_per_shot.get("zScore"))
    shots_on_target = comp("shotOnTargetRate")
    sot_z = _to_float_or_none(shots_on_target.get("zScore"))
    if xg_z is not None and xg_z < -1.0:
        severity = _z_based_weakness_score(xg_z, threshold=-1.0)
        if sot_z is not None and sot_z < -0.5:
            severity = _clamp(severity + 0.15, 0.0, 1.0)
        add_insight(
            insight_type="final_third",
            title="Low-quality shot profile",
            message="Chance quality per shot is below league baseline.",
            recommendation="Shift final-third actions toward central cutbacks and higher-probability shooting zones.",
            severity_score=severity,
            evidence={
                **_metric_evidence("xgPerShot", xg_per_shot),
                "supportingMetric": _metric_evidence("shotOnTargetRate", shots_on_target),
            },
        )

    box_eff = comp("boxEfficiency")
    z = _to_float_or_none(box_eff.get("zScore"))
    if z is not None and z < -1.0:
        add_insight(
            insight_type="final_third",
            title="Poor box efficiency",
            message="Final-third box actions convert into low xG output versus league baseline.",
            recommendation="Improve shot selection and box occupation timing before finishing.",
            severity_score=_z_based_weakness_score(z, threshold=-1.0),
            evidence=_metric_evidence("boxEfficiency", box_eff),
        )

    z = _to_float_or_none(shots_on_target.get("zScore"))
    if z is not None and z < -1.0:
        add_insight(
            insight_type="final_third",
            title="Low shot accuracy",
            message="Shot-on-target rate is below league baseline.",
            recommendation="Create cleaner finishing scenarios and reduce low-balance attempts.",
            severity_score=_z_based_weakness_score(z, threshold=-1.0),
            evidence=_metric_evidence("shotOnTargetRate", shots_on_target),
        )

    # Pressing rules
    counterpress = comp("counterpressingRate")
    percentile = _to_float_or_none(counterpress.get("percentile"))
    if percentile is not None and percentile < 25.0:
        add_insight(
            insight_type="pressing",
            title="Low counterpressing impact",
            message="Counterpressing recovery rate is in the bottom quartile.",
            recommendation="Compress distances around ball loss and trigger immediate pressure with nearest support.",
            severity_score=_percentile_low_score(percentile, threshold=25.0),
            evidence=_metric_evidence("counterpressingRate", counterpress),
        )

    high_recovery = comp("highRecoveryRate")
    percentile = _to_float_or_none(high_recovery.get("percentile"))
    if percentile is not None and percentile < 25.0:
        add_insight(
            insight_type="pressing",
            title="Few high recoveries",
            message="Opponent-half recovery rate is below league baseline.",
            recommendation="Improve coordinated pressure to win more second balls in advanced zones.",
            severity_score=_percentile_low_score(percentile, threshold=25.0),
            evidence=_metric_evidence("highRecoveryRate", high_recovery),
        )

    pressing_duel = comp("pressingDuelSuccessRate")
    percentile = _to_float_or_none(pressing_duel.get("percentile"))
    if percentile is not None and percentile < 25.0:
        add_insight(
            insight_type="pressing",
            title="Low pressing duel success",
            message="Pressing duel success is in the bottom quartile.",
            recommendation="Refine pressing body shape and first contact timing to improve duel outcomes.",
            severity_score=_percentile_low_score(percentile, threshold=25.0),
            evidence=_metric_evidence("pressingDuelSuccessRate", pressing_duel),
        )

    # Duel rules
    duel = comp("duelSuccessRate")
    percentile = _to_float_or_none(duel.get("percentile"))
    if percentile is not None and percentile < 25.0:
        add_insight(
            insight_type="duels",
            title="Low duel success",
            message="Overall duel success is below league reference values.",
            recommendation="Improve duel preparation distances and support structure around contested zones.",
            severity_score=_percentile_low_score(percentile, threshold=25.0),
            evidence=_metric_evidence("duelSuccessRate", duel),
        )

    defensive_duel = comp("defensiveDuelSuccessRate")
    percentile = _to_float_or_none(defensive_duel.get("percentile"))
    if percentile is not None and percentile < 25.0:
        add_insight(
            insight_type="duels",
            title="Defensive duel weakness",
            message="Defensive duel win rate is in the bottom quartile.",
            recommendation="Improve first-contact timing and cover-shadow positioning in defensive duels.",
            severity_score=_percentile_low_score(percentile, threshold=25.0),
            evidence=_metric_evidence("defensiveDuelSuccessRate", defensive_duel),
        )

    aerial_duel = comp("aerialDuelSuccessRate")
    percentile = _to_float_or_none(aerial_duel.get("percentile"))
    if percentile is not None and percentile < 25.0:
        add_insight(
            insight_type="duels",
            title="Aerial duel weakness",
            message="Aerial duel win rate is below league baseline.",
            recommendation="Improve second-ball positioning and timing on aerial contests.",
            severity_score=_percentile_low_score(percentile, threshold=25.0),
            evidence=_metric_evidence("aerialDuelSuccessRate", aerial_duel),
        )

    return insights


def _metric_evidence(metric_name: str, comp_metric: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric": metric_name,
        "value": _round_optional(_to_float_or_none(comp_metric.get("value"))),
        "leagueAverage": _round_optional(_to_float_or_none(comp_metric.get("leagueAverage"))),
        "zScore": _round_optional(_to_float_or_none(comp_metric.get("zScore"))),
        "percentile": _round_optional(_to_float_or_none(comp_metric.get("percentile"))),
    }


def _z_based_weakness_score(z_score: float, threshold: float) -> float:
    # Works for thresholds in the weak direction (e.g., z < -1.0 for positive metrics).
    gap = max(0.0, threshold - z_score)
    return _clamp(gap / 1.5, 0.0, 1.0)


def _percentile_low_score(percentile: float, threshold: float) -> float:
    return _clamp((threshold - percentile) / threshold, 0.0, 1.0)


def _percentile_high_score(percentile: float, threshold: float) -> float:
    return _clamp((percentile - threshold) / (100.0 - threshold), 0.0, 1.0)


def _severity_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _index_team_rows(rows: list[dict[str, Any]]) -> dict[tuple[int | None, int | None], dict[str, Any]]:
    out: dict[tuple[int | None, int | None], dict[str, Any]] = {}
    for row in rows:
        match_id = _to_int(row.get("match_id"))
        team_id = _to_int(row.get("team_id"))
        out[(match_id, team_id)] = row
    return out


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


def _round_optional(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
