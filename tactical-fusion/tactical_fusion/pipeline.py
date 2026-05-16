from __future__ import annotations

from typing import Any

from tactical_fusion.api import build_frontend_output, build_fusion_output
from tactical_fusion.config import resolve_calibration_config
from tactical_fusion.fusion import fuse_signals
from tactical_fusion.ingestion import validate_input1, validate_input2
from tactical_fusion.insights import (
    generate_insights,
    generate_player_priorities,
    generate_training_focus,
)
from tactical_fusion.normalization import normalize_input1, normalize_input2


def run_fusion(
    input1: dict[str, Any],
    input2: dict[str, Any],
    calibration_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = resolve_calibration_config(calibration_config)
    validate_input1(input1)
    validate_input2(input2)

    baseline_signals = normalize_input1(input1)
    decision_signals = normalize_input2(input2)
    fused_signals = fuse_signals(
        baseline_signals,
        decision_signals,
        baseline_weight=config["baseline_weight"],
        decision_weight=config["decision_weight"],
    )

    insights = generate_insights(
        fused_signals,
        severity_thresholds=config["severity_thresholds"],
    )
    player_priorities = generate_player_priorities(decision_signals)
    training_focus = generate_training_focus(
        fused_signals,
        severity_thresholds=config["severity_thresholds"],
    )

    fusion_output = build_fusion_output(
        insights=insights,
        player_priorities=player_priorities,
        training_focus=training_focus,
    )
    frontend_output = build_frontend_output(fusion_output)
    return {
        "fusionOutput": fusion_output,
        "frontendOutput": frontend_output,
        "meta": {
            "baselineSignals": len(baseline_signals),
            "decisionSignals": len(decision_signals),
            "fusedCategories": len(fused_signals),
            "calibration": config,
        },
    }
