from __future__ import annotations

from typing import Final

from tactical_fusion.models import TacticalCategory

CATEGORIES: Final[set[TacticalCategory]] = {
    "build_up",
    "ball_loss",
    "progression",
    "final_third",
    "duels",
    "pressing",
}

METRIC_TO_CATEGORY: Final[dict[str, TacticalCategory]] = {
    "progressivePassSuccessRate": "build_up",
    "finalThirdPassSuccessRate": "build_up",
    "passSuccessRate": "build_up",
    "forwardPassSuccessRate": "progression",
    "lossRate": "ball_loss",
    "ownHalfLossRate": "ball_loss",
    "dangerousLossRate": "ball_loss",
    "xgPerShot": "final_third",
    "boxEfficiency": "final_third",
    "shotOnTargetRate": "final_third",
    "duelSuccessRate": "duels",
    "defensiveDuelSuccessRate": "duels",
    "offensiveDuelSuccessRate": "duels",
    "aerialDuelSuccessRate": "duels",
    "highRecoveryRate": "pressing",
    "counterpressingRate": "pressing",
}

DECISION_TO_CATEGORY: Final[dict[str, TacticalCategory]] = {
    "pass": "build_up",
    "carry": "progression",
    "shot": "final_third",
}

WEAK_DECISION_TO_CATEGORY: Final[dict[str, TacticalCategory]] = {
    "pass": "build_up",
    "carry": "progression",
    "shot": "final_third",
}

SEVERITY_LABEL_TO_SCORE: Final[dict[str, float]] = {
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "critical": 0.95,
}
