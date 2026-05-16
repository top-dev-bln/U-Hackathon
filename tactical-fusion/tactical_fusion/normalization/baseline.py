from __future__ import annotations

from typing import Any

from tactical_fusion.models import BaselineSignal

from .common import clamp01, safe_float
from .taxonomy import CATEGORIES, METRIC_TO_CATEGORY, SEVERITY_LABEL_TO_SCORE


def _normalize_baseline_signal(signal: dict[str, Any]) -> BaselineSignal | None:
    category = signal.get("category")
    metric = str(signal.get("metric", "unknown"))
    if category not in CATEGORIES:
        category = METRIC_TO_CATEGORY.get(metric)
    if category is None:
        return None

    score_from_numeric = safe_float(signal.get("severityScore"), default=-1.0)
    if score_from_numeric >= 0:
        severity = clamp01(score_from_numeric)
    else:
        severity = SEVERITY_LABEL_TO_SCORE.get(str(signal.get("severity", "")).lower(), 0.5)

    return BaselineSignal(
        category=category,
        severity=severity,
        metric=metric,
        signal_id=str(signal.get("signalId", metric)),
    )


def normalize_input1(payload: dict[str, Any]) -> list[BaselineSignal]:
    raw_signals = payload.get("weaknessSignals", [])
    normalized: list[BaselineSignal] = []
    for raw_signal in raw_signals:
        if not isinstance(raw_signal, dict):
            continue
        signal = _normalize_baseline_signal(raw_signal)
        if signal is not None:
            normalized.append(signal)
    return normalized
