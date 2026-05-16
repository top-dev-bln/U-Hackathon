from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_CALIBRATION_CONFIG: dict[str, Any] = {
    "baseline_weight": 0.55,
    "decision_weight": 0.45,
    "severity_thresholds": {
        "medium": 0.4,
        "high": 0.6,
        "critical": 0.8,
    },
}


def _normalized_weights(baseline_weight: float, decision_weight: float) -> tuple[float, float]:
    total = baseline_weight + decision_weight
    if total <= 0:
        return 0.55, 0.45
    return baseline_weight / total, decision_weight / total


def _normalized_thresholds(thresholds: dict[str, Any]) -> dict[str, float]:
    medium = float(thresholds.get("medium", 0.4))
    high = float(thresholds.get("high", 0.6))
    critical = float(thresholds.get("critical", 0.8))

    medium = max(0.0, min(1.0, medium))
    high = max(medium + 0.01, min(1.0, high))
    critical = max(high + 0.01, min(1.0, critical))
    if critical > 1.0:
        critical = 1.0
        high = min(high, 0.99)
        medium = min(medium, 0.98)
    return {"medium": medium, "high": high, "critical": critical}


def resolve_calibration_config(override: dict[str, Any] | None = None) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CALIBRATION_CONFIG)
    if not override:
        bw, dw = _normalized_weights(
            float(config["baseline_weight"]),
            float(config["decision_weight"]),
        )
        config["baseline_weight"] = bw
        config["decision_weight"] = dw
        config["severity_thresholds"] = _normalized_thresholds(config["severity_thresholds"])
        return config

    if "baseline_weight" in override:
        config["baseline_weight"] = float(override["baseline_weight"])
    if "decision_weight" in override:
        config["decision_weight"] = float(override["decision_weight"])
    if "severity_thresholds" in override and isinstance(override["severity_thresholds"], dict):
        merged_thresholds = dict(config["severity_thresholds"])
        merged_thresholds.update(override["severity_thresholds"])
        config["severity_thresholds"] = merged_thresholds

    bw, dw = _normalized_weights(
        float(config["baseline_weight"]),
        float(config["decision_weight"]),
    )
    config["baseline_weight"] = bw
    config["decision_weight"] = dw
    config["severity_thresholds"] = _normalized_thresholds(config["severity_thresholds"])
    return config
