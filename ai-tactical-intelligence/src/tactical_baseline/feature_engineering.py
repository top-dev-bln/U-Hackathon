from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any


METRIC_DIRECTIONS: dict[str, str] = {
    "passSuccessRate": "higher_is_better",
    "progressivePassSuccessRate": "higher_is_better",
    "finalThirdPassSuccessRate": "higher_is_better",
    "forwardPassSuccessRate": "higher_is_better",
    "progressivePassShare": "higher_is_better",
    "finalThirdEntryShare": "higher_is_better",
    "lossRate": "higher_is_worse",
    "ownHalfLossRate": "higher_is_worse",
    "dangerousLossRate": "higher_is_worse",
    "shotOnTargetRate": "higher_is_better",
    "xgPerShot": "higher_is_better",
    "boxEfficiency": "higher_is_better",
    "counterpressingRate": "higher_is_better",
    "highRecoveryRate": "higher_is_better",
    "duelSuccessRate": "higher_is_better",
    "defensiveDuelSuccessRate": "higher_is_better",
    "offensiveDuelSuccessRate": "higher_is_better",
    "aerialDuelSuccessRate": "higher_is_better",
    "pressingDuelSuccessRate": "higher_is_better",
}


@dataclass
class TeamFeatureEngineeringResult:
    fieldnames: list[str]
    rows: list[dict[str, Any]]
    report_payload: dict[str, Any]
    metric_directions: dict[str, str]


def build_team_match_features(
    team_rows: list[dict[str, Any]],
    team_fieldnames: list[str],
) -> TeamFeatureEngineeringResult:
    output_rows: list[dict[str, Any]] = [dict(row) for row in team_rows]
    denominator_zero_counts: Counter[str] = Counter()
    rows_with_nonfinite_values = 0

    for row in output_rows:
        computed = _compute_row_features(row, denominator_zero_counts)
        has_nonfinite = False
        for metric_name, metric_value in computed.items():
            if not math.isfinite(metric_value):
                metric_value = 0.0
                has_nonfinite = True
            row[metric_name] = metric_value
        if has_nonfinite:
            rows_with_nonfinite_values += 1

    derived_metric_names = list(METRIC_DIRECTIONS.keys())
    fieldnames = list(team_fieldnames) + [m for m in derived_metric_names if m not in team_fieldnames]

    report_payload = {
        "totals": {
            "input_rows": len(team_rows),
            "output_rows": len(output_rows),
            "derived_metrics_count": len(derived_metric_names),
        },
        "validations": {
            "rows_with_nonfinite_values": rows_with_nonfinite_values,
            "all_rows_finite": rows_with_nonfinite_values == 0,
        },
        "denominator_zero_counts": dict(denominator_zero_counts),
        "derived_metrics": derived_metric_names,
    }

    return TeamFeatureEngineeringResult(
        fieldnames=fieldnames,
        rows=output_rows,
        report_payload=report_payload,
        metric_directions=dict(METRIC_DIRECTIONS),
    )


def _compute_row_features(row: dict[str, Any], denominator_zero_counts: Counter[str]) -> dict[str, float]:
    values = {
        "total_successfulPasses": _to_float(row.get("total_successfulPasses")),
        "total_passes": _to_float(row.get("total_passes")),
        "total_successfulProgressivePasses": _to_float(row.get("total_successfulProgressivePasses")),
        "total_progressivePasses": _to_float(row.get("total_progressivePasses")),
        "total_successfulPassesToFinalThird": _to_float(row.get("total_successfulPassesToFinalThird")),
        "total_passesToFinalThird": _to_float(row.get("total_passesToFinalThird")),
        "total_successfulForwardPasses": _to_float(row.get("total_successfulForwardPasses")),
        "total_forwardPasses": _to_float(row.get("total_forwardPasses")),
        "total_losses": _to_float(row.get("total_losses")),
        "total_ownHalfLosses": _to_float(row.get("total_ownHalfLosses")),
        "total_dangerousOwnHalfLosses": _to_float(row.get("total_dangerousOwnHalfLosses")),
        "total_dribbles": _to_float(row.get("total_dribbles")),
        "total_receivedPass": _to_float(row.get("total_receivedPass")),
        "total_shotsOnTarget": _to_float(row.get("total_shotsOnTarget")),
        "total_shots": _to_float(row.get("total_shots")),
        "total_xgShot": _to_float(row.get("total_xgShot")),
        "total_touchInBox": _to_float(row.get("total_touchInBox")),
        "total_counterpressingRecoveries": _to_float(row.get("total_counterpressingRecoveries")),
        "total_recoveries": _to_float(row.get("total_recoveries")),
        "total_opponentHalfRecoveries": _to_float(row.get("total_opponentHalfRecoveries")),
        "total_duelsWon": _to_float(row.get("total_duelsWon")),
        "total_duels": _to_float(row.get("total_duels")),
        "total_defensiveDuelsWon": _to_float(row.get("total_defensiveDuelsWon")),
        "total_defensiveDuels": _to_float(row.get("total_defensiveDuels")),
        "total_offensiveDuelsWon": _to_float(row.get("total_offensiveDuelsWon")),
        "total_offensiveDuels": _to_float(row.get("total_offensiveDuels")),
        "total_aerialDuelsWon": _to_float(row.get("total_aerialDuelsWon")),
        "total_aerialDuels": _to_float(row.get("total_aerialDuels")),
        "total_pressingDuelsWon": _to_float(row.get("total_pressingDuelsWon")),
        "total_pressingDuels": _to_float(row.get("total_pressingDuels")),
    }

    results: dict[str, float] = {}
    results["passSuccessRate"] = _safe_div(
        values["total_successfulPasses"], values["total_passes"], "passSuccessRate", denominator_zero_counts
    )
    results["progressivePassSuccessRate"] = _safe_div(
        values["total_successfulProgressivePasses"],
        values["total_progressivePasses"],
        "progressivePassSuccessRate",
        denominator_zero_counts,
    )
    results["finalThirdPassSuccessRate"] = _safe_div(
        values["total_successfulPassesToFinalThird"],
        values["total_passesToFinalThird"],
        "finalThirdPassSuccessRate",
        denominator_zero_counts,
    )
    results["forwardPassSuccessRate"] = _safe_div(
        values["total_successfulForwardPasses"],
        values["total_forwardPasses"],
        "forwardPassSuccessRate",
        denominator_zero_counts,
    )
    results["progressivePassShare"] = _safe_div(
        values["total_progressivePasses"], values["total_passes"], "progressivePassShare", denominator_zero_counts
    )
    results["finalThirdEntryShare"] = _safe_div(
        values["total_passesToFinalThird"], values["total_passes"], "finalThirdEntryShare", denominator_zero_counts
    )

    loss_denom = values["total_passes"] + values["total_dribbles"] + values["total_receivedPass"]
    results["lossRate"] = _safe_div(values["total_losses"], loss_denom, "lossRate", denominator_zero_counts)
    results["ownHalfLossRate"] = _safe_div(
        values["total_ownHalfLosses"], values["total_losses"], "ownHalfLossRate", denominator_zero_counts
    )
    results["dangerousLossRate"] = _safe_div(
        values["total_dangerousOwnHalfLosses"], values["total_losses"], "dangerousLossRate", denominator_zero_counts
    )

    results["shotOnTargetRate"] = _safe_div(
        values["total_shotsOnTarget"], values["total_shots"], "shotOnTargetRate", denominator_zero_counts
    )
    results["xgPerShot"] = _safe_div(values["total_xgShot"], values["total_shots"], "xgPerShot", denominator_zero_counts)
    results["boxEfficiency"] = _safe_div(
        values["total_xgShot"], values["total_touchInBox"], "boxEfficiency", denominator_zero_counts
    )

    results["counterpressingRate"] = _safe_div(
        values["total_counterpressingRecoveries"],
        values["total_recoveries"],
        "counterpressingRate",
        denominator_zero_counts,
    )
    results["highRecoveryRate"] = _safe_div(
        values["total_opponentHalfRecoveries"],
        values["total_recoveries"],
        "highRecoveryRate",
        denominator_zero_counts,
    )

    results["duelSuccessRate"] = _safe_div(
        values["total_duelsWon"], values["total_duels"], "duelSuccessRate", denominator_zero_counts
    )
    results["defensiveDuelSuccessRate"] = _safe_div(
        values["total_defensiveDuelsWon"],
        values["total_defensiveDuels"],
        "defensiveDuelSuccessRate",
        denominator_zero_counts,
    )
    results["offensiveDuelSuccessRate"] = _safe_div(
        values["total_offensiveDuelsWon"],
        values["total_offensiveDuels"],
        "offensiveDuelSuccessRate",
        denominator_zero_counts,
    )
    results["aerialDuelSuccessRate"] = _safe_div(
        values["total_aerialDuelsWon"], values["total_aerialDuels"], "aerialDuelSuccessRate", denominator_zero_counts
    )
    results["pressingDuelSuccessRate"] = _safe_div(
        values["total_pressingDuelsWon"],
        values["total_pressingDuels"],
        "pressingDuelSuccessRate",
        denominator_zero_counts,
    )

    return results


def _safe_div(numerator: float, denominator: float, metric_name: str, counters: Counter[str]) -> float:
    if denominator == 0:
        counters[metric_name] += 1
        return 0.0
    return numerator / denominator


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
