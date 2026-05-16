from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from tactical_fusion.models import DecisionSignal

from .common import clamp01, safe_float
from .taxonomy import DECISION_TO_CATEGORY, WEAK_DECISION_TO_CATEGORY


def _decision_category(decision: str | None, fallback: str = "progression") -> str:
    if decision is None:
        return fallback
    return DECISION_TO_CATEGORY.get(decision.lower(), fallback)


def _severity_from_phase(decision_value: float, potential_gain: float) -> float:
    low_decision_penalty = max(0.0, 0.25 - decision_value) * 1.4
    gain_boost = potential_gain * 4.0
    return clamp01(0.3 + low_decision_penalty + gain_boost)


def _iter_dicts(items: object) -> Iterable[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    return (item for item in items if isinstance(item, dict))


def _normalize_improvable_phases(phases: list[dict[str, Any]]) -> list[DecisionSignal]:
    normalized: list[DecisionSignal] = []
    for phase in phases:
        decision = phase.get("decision")
        category = _decision_category(str(decision) if decision else None)
        severity = _severity_from_phase(
            decision_value=safe_float(phase.get("decisionValue")),
            potential_gain=safe_float(phase.get("potentialGain")),
        )
        normalized.append(
            DecisionSignal(
                category=category,
                severity=severity,
                players=[str(phase.get("player_name", "unknown"))],
                decision_type=str(decision) if decision is not None else None,
                reason="improvable_phase",
            )
        )
    return normalized


def _normalize_missed_opportunities(phases: list[dict[str, Any]]) -> list[DecisionSignal]:
    normalized: list[DecisionSignal] = []
    for phase in phases:
        severity = clamp01(0.45 + safe_float(phase.get("potentialGain")) * 3.5)
        normalized.append(
            DecisionSignal(
                category="final_third",
                severity=severity,
                players=[str(phase.get("player_name", "unknown"))],
                decision_type=str(phase.get("decision")) if phase.get("decision") is not None else None,
                reason="missed_shot_or_goal_opportunity",
            )
        )
    return normalized


def _normalize_needs_support(players: list[dict[str, Any]]) -> list[DecisionSignal]:
    normalized: list[DecisionSignal] = []
    for player in players:
        weak_decision_type = str(player.get("weakDecisionType", "")).lower() or None
        category = WEAK_DECISION_TO_CATEGORY.get(weak_decision_type or "", "ball_loss")
        decision_score = safe_float(player.get("decisionScore"), default=0.2)
        low_score_actions = safe_float(player.get("lowScoreActions"), default=0.0)
        actions_analyzed = max(1.0, safe_float(player.get("actionsAnalyzed"), default=1.0))

        low_action_ratio = low_score_actions / actions_analyzed
        severity = clamp01((1.0 - decision_score) * 0.75 + low_action_ratio * 0.5)

        normalized.append(
            DecisionSignal(
                category=category,
                severity=severity,
                players=[str(player.get("player_name", "unknown"))],
                decision_type=weak_decision_type,
                reason="player_needs_support",
            )
        )
    return normalized


def _normalize_team_decisions(team_decisions: list[dict[str, Any]]) -> list[DecisionSignal]:
    normalized: list[DecisionSignal] = []
    for row in team_decisions:
        decision = str(row.get("decision", "")).lower() or None
        category = _decision_category(decision)
        avg_decision_value = safe_float(row.get("avgDecisionValue"), default=0.2)
        low_phases = safe_float(row.get("lowDecisionPhases"), default=0.0)
        actions = max(1.0, safe_float(row.get("actions"), default=1.0))
        low_ratio = low_phases / actions
        severity = clamp01((0.25 - avg_decision_value) * 1.8 + low_ratio)
        normalized.append(
            DecisionSignal(
                category=category,
                severity=severity,
                players=[],
                decision_type=decision,
                reason="low_decision_phases",
            )
        )
    return normalized


def normalize_input2(payload: dict[str, Any]) -> list[DecisionSignal]:
    phases = payload.get("phases", {})
    players = payload.get("players", {})
    team_stats = payload.get("teamStats", {})

    improvable = _normalize_improvable_phases(
        list(_iter_dicts(phases.get("improvablePhases")))
    )
    missed = _normalize_missed_opportunities(
        list(_iter_dicts(phases.get("missedShotOrGoalOpportunities")))
    )
    support = _normalize_needs_support(
        list(_iter_dicts(players.get("needsSupport")))
    )
    decision_by_type = _normalize_team_decisions(
        list(_iter_dicts(team_stats.get("decisionByType")))
    )
    return improvable + missed + support + decision_by_type
