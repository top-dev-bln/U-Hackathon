from __future__ import annotations

from collections import defaultdict

from tactical_fusion.models import DecisionSignal, FusedSignal, Insight, PlayerPriority, TrainingFocus


def _severity_band(score: float, thresholds: dict[str, float] | None = None) -> str:
    effective_thresholds = thresholds or {"medium": 0.4, "high": 0.6, "critical": 0.8}
    if score >= effective_thresholds["critical"]:
        return "critical"
    if score >= effective_thresholds["high"]:
        return "high"
    if score >= effective_thresholds["medium"]:
        return "medium"
    return "low"


MESSAGE_TEMPLATES: dict[str, str] = {
    "build_up": "Build-up actions are unstable and reduce controlled progression.",
    "ball_loss": "Ball retention risk is high and creates transition exposure.",
    "progression": "Progression quality is inconsistent and limits vertical threat.",
    "final_third": "Final-third decisions reduce conversion probability.",
    "duels": "Duel execution is below target in key contests.",
    "pressing": "Pressing effectiveness is below tactical target.",
}

RECOMMENDATION_TEMPLATES: dict[str, str] = {
    "build_up": "Train press-resistant passing triangles with one-touch escape patterns.",
    "ball_loss": "Add constrained rondo and own-half exit drills under directional pressure.",
    "progression": "Run third-man progression patterns with carry-vs-pass decision triggers.",
    "final_third": "Use shot selection circuits with pre-shot scan constraints.",
    "duels": "Increase aerial and shoulder-contact duel repetitions by role group.",
    "pressing": "Drill coordinated counterpressing with first-5-second recovery targets.",
}

TRAINING_OBJECTIVE: dict[str, tuple[str, str]] = {
    "build_up": (
        "Increase pass security under pressure",
        "6v4 build-up under press with mandatory support angles",
    ),
    "ball_loss": (
        "Reduce dangerous turnovers in own half",
        "Directional rondo with immediate transition punishment",
    ),
    "progression": (
        "Improve vertical progression timing",
        "Third-man run and carry release circuit",
    ),
    "final_third": (
        "Improve chance conversion decisions",
        "Final-third scenario game with shot/pass quality gates",
    ),
    "duels": (
        "Improve duel win rate in contested zones",
        "Aerial timing and body-position duel blocks",
    ),
    "pressing": (
        "Increase high recoveries after loss",
        "Counterpressing wave drill with compactness scoring",
    ),
}

PLAYER_ACTION_BY_CATEGORY: dict[str, str] = {
    "build_up": "Review build-up decisions under pressure.",
    "ball_loss": "Work on safer retention choices in own-half circulation.",
    "progression": "Improve carry-vs-pass timing for progression phases.",
    "final_third": "Review final-third pass/shot selection in constrained scenarios.",
    "duels": "Improve duel timing and body orientation in contested situations.",
    "pressing": "Improve pressing trigger recognition and first reaction speed.",
}


def generate_insights(
    fused_signals: list[FusedSignal],
    top_n: int = 5,
    severity_thresholds: dict[str, float] | None = None,
) -> list[Insight]:
    insights: list[Insight] = []
    for fused in fused_signals[:top_n]:
        insights.append(
            Insight(
                type=f"risky_{fused.category}",
                category=fused.category,
                severity=_severity_band(fused.combined_score, severity_thresholds),
                score=round(fused.combined_score, 4),
                confidence=round(fused.confidence, 4),
                message=MESSAGE_TEMPLATES[fused.category],
                recommendation=RECOMMENDATION_TEMPLATES[fused.category],
                players=fused.players[:4],
                evidence={
                    "baselineSignals": fused.baseline_evidence,
                    "decisionSignals": fused.decision_evidence,
                },
            )
        )
    return insights


def _recommended_action(focus_categories: list[str]) -> str:
    if not focus_categories:
        return "Review low-value decisions from recent match phases."
    primary = focus_categories[0]
    return PLAYER_ACTION_BY_CATEGORY.get(
        primary,
        "Review low-value decisions from recent match phases.",
    )


def generate_player_priorities(
    decision_signals: list[DecisionSignal],
    top_n: int = 5,
) -> list[PlayerPriority]:
    if not decision_signals:
        return []

    severity_sum: dict[str, float] = defaultdict(float)
    involvement: dict[str, int] = defaultdict(int)
    categories: dict[str, set[str]] = defaultdict(set)
    reasons: dict[str, set[str]] = defaultdict(set)

    for signal in decision_signals:
        if not signal.players:
            continue
        for player in signal.players:
            severity_sum[player] += signal.severity
            involvement[player] += 1
            categories[player].add(signal.category)
            if signal.reason:
                reasons[player].add(signal.reason)

    ranked: list[PlayerPriority] = []
    for player, total in severity_sum.items():
        count = involvement[player]
        priority_score = min(1.0, (total / count) * 0.75 + min(0.25, count * 0.03))
        focus_categories = sorted(categories[player])
        ranked.append(
            PlayerPriority(
                player=player,
                priority_score=round(priority_score, 4),
                reasons=sorted(reasons[player]),
                focus_categories=focus_categories,
                recommendedAction=_recommended_action(focus_categories),
            )
        )

    ranked.sort(key=lambda row: row.priority_score, reverse=True)
    return ranked[:top_n]


def generate_training_focus(
    fused_signals: list[FusedSignal],
    top_n: int = 3,
    severity_thresholds: dict[str, float] | None = None,
) -> list[TrainingFocus]:
    focus: list[TrainingFocus] = []
    for fused in fused_signals[:top_n]:
        objective, drill = TRAINING_OBJECTIVE[fused.category]
        focus.append(
            TrainingFocus(
                category=fused.category,
                priority=_severity_band(fused.combined_score, severity_thresholds),
                objective=objective,
                drill=drill,
            )
        )
    return focus
