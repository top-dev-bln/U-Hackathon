from __future__ import annotations

from typing import Any


def get_path(data: Any, path: str, default: Any = None) -> Any:
    current = data
    for token in path.split("."):
        if isinstance(current, dict):
            current = current.get(token, default)
        elif isinstance(current, list):
            try:
                index = int(token)
            except ValueError:
                return default
            if index < 0 or index >= len(current):
                return default
            current = current[index]
        else:
            return default
        if current is None:
            return default
    return current


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

