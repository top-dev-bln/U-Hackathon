from __future__ import annotations

from tactical_fusion.models import Insight, PlayerPriority, TrainingFocus

HEADLINE_BY_TYPE = {
    "risky_build_up": "Build-up instability is the main tactical risk",
    "risky_ball_loss": "Ball-loss risk is the main tactical concern",
    "risky_progression": "Progression consistency is the main tactical risk",
    "risky_final_third": "Final-third decision quality is the main tactical risk",
    "risky_duels": "Duel execution is the main tactical risk",
    "risky_pressing": "Pressing effectiveness is the main tactical risk",
}


def build_fusion_output(
    insights: list[Insight],
    player_priorities: list[PlayerPriority],
    training_focus: list[TrainingFocus],
) -> dict:
    return {
        "combinedInsights": [row.to_dict() for row in insights],
        "playerPriorities": [row.to_dict() for row in player_priorities],
        "trainingFocus": [row.to_dict() for row in training_focus],
    }


def build_frontend_output(fusion_output: dict) -> dict:
    insights = fusion_output.get("combinedInsights", [])
    top_problems = [
        {
            "type": insight.get("type"),
            "severity": insight.get("severity"),
            "message": insight.get("message"),
            "score": insight.get("score"),
        }
        for insight in insights[:3]
    ]
    recommendations = [insight.get("recommendation") for insight in insights[:3]]
    if top_problems:
        top_type = top_problems[0]["type"]
        headline = HEADLINE_BY_TYPE.get(top_type, "Top tactical risk identified from current match profile")
    else:
        headline = "No tactical risks detected from current inputs"
    return {
        "headline": headline,
        "topProblems": top_problems,
        "recommendations": recommendations,
    }
