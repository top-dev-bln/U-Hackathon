from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    pass


def _ensure_dict(value: Any, field_path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"`{field_path}` must be an object")
    return value


def _ensure_list(value: Any, field_path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"`{field_path}` must be an array")
    return value


def _require_fields(source: dict[str, Any], fields: list[str], field_path: str) -> None:
    missing = [field for field in fields if field not in source]
    if missing:
        raise ValidationError(f"Missing required fields in `{field_path}`: {', '.join(missing)}")


def validate_input1(payload: dict[str, Any]) -> None:
    root = _ensure_dict(payload, "input1")
    _require_fields(
        root,
        ["baselineModel", "weaknessSignals", "metricComparisons"],
        "input1",
    )

    baseline_model = _ensure_dict(root["baselineModel"], "input1.baselineModel")
    _require_fields(
        baseline_model,
        ["overallWeaknessScore", "riskLevel", "tacticalProfile", "anomalyScore"],
        "input1.baselineModel",
    )

    weakness_signals = _ensure_list(root["weaknessSignals"], "input1.weaknessSignals")
    for index, signal in enumerate(weakness_signals):
        signal_dict = _ensure_dict(signal, f"input1.weaknessSignals[{index}]")
        _require_fields(
            signal_dict,
            ["signalId", "category", "severityScore", "metric"],
            f"input1.weaknessSignals[{index}]",
        )

    _ensure_dict(root["metricComparisons"], "input1.metricComparisons")


def validate_input2(payload: dict[str, Any]) -> None:
    root = _ensure_dict(payload, "input2")
    _require_fields(root, ["summary", "players", "phases", "teamStats"], "input2")

    summary = _ensure_dict(root["summary"], "input2.summary")
    _require_fields(
        summary,
        [
            "averageDecisionValue",
            "lowDecisionPhases",
            "phasesWithAlternative",
            "missedShotOrGoalOpportunities",
        ],
        "input2.summary",
    )

    players = _ensure_dict(root["players"], "input2.players")
    _require_fields(players, ["needsSupport"], "input2.players")
    _ensure_list(players["needsSupport"], "input2.players.needsSupport")

    phases = _ensure_dict(root["phases"], "input2.phases")
    _require_fields(
        phases,
        ["improvablePhases", "missedShotOrGoalOpportunities"],
        "input2.phases",
    )
    _ensure_list(phases["improvablePhases"], "input2.phases.improvablePhases")
    _ensure_list(
        phases["missedShotOrGoalOpportunities"],
        "input2.phases.missedShotOrGoalOpportunities",
    )

    team_stats = _ensure_dict(root["teamStats"], "input2.teamStats")
    _require_fields(team_stats, ["decisionByType", "timeline"], "input2.teamStats")
    _ensure_list(team_stats["decisionByType"], "input2.teamStats.decisionByType")
    _ensure_list(team_stats["timeline"], "input2.teamStats.timeline")
