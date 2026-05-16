from __future__ import annotations

from typing import Any


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("message", "recommendation", "category", "type", "label", "name"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        baseline_signals = value.get("baselineSignals")
        decision_signals = value.get("decisionSignals")
        if isinstance(baseline_signals, list) or isinstance(decision_signals, list):
            return (
                f"baseline signals: {to_sentence(list(baseline_signals or []), max_items=4)}; "
                f"decision signals: {to_sentence(list(decision_signals or []), max_items=4)}"
            )
        parts = []
        for key in ("metric", "severity", "player", "score", "value"):
            if key in value:
                parts.append(f"{key}={value[key]}")
        if parts:
            return ", ".join(parts)
        return str(value)
    if isinstance(value, list):
        return to_sentence(value, max_items=4)
    return str(value).strip()


def to_sentence(values: list[Any], max_items: int = 6) -> str:
    filtered = [_stringify(v) for v in values]
    filtered = [v for v in filtered if v]
    if not filtered:
        return "none"
    clipped = filtered[:max_items]
    if len(clipped) == 1:
        return clipped[0]
    if len(clipped) == 2:
        return f"{clipped[0]} and {clipped[1]}"
    return ", ".join(clipped[:-1]) + f", and {clipped[-1]}"


def safe_text(value: Any, fallback: str = "n/a") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback
