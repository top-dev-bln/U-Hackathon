from __future__ import annotations


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
