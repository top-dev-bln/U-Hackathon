from typing import Any


def _player_location(event: dict, player_id: int) -> tuple[float, float] | None:
    """Where this player was in this event — his own location, or endLocation if he received a pass."""
    if (event.get("player") or {}).get("id") == player_id:
        loc = event.get("location") or {}
        if loc.get("x") is not None and loc.get("y") is not None:
            return (loc["x"], loc["y"])
        return None
    pass_data = event.get("pass") or {}
    if ((pass_data.get("recipient") or {}).get("id") == player_id
            and pass_data.get("accurate")):
        end = pass_data.get("endLocation") or {}
        if end.get("x") is not None and end.get("y") is not None:
            return (end["x"], end["y"])
    return None


def build_player_profile(
    events: list[dict[str, Any]],
    player_id: int,
    period: str = "full",
    grid_cols: int = 12,
    grid_rows: int = 8,
) -> dict | None:
    points: list[tuple[float, float]] = []
    receptions = 0
    player_info: dict | None = None
    team_info: dict | None = None

    for e in events:
        if period in ("1H", "2H") and e.get("matchPeriod") != period:
            continue

        p = e.get("player") or {}
        if p.get("id") == player_id and player_info is None:
            player_info = {
                "id": player_id,
                "name": p.get("name", "?"),
                "position": p.get("position", "?"),
            }
            t = e.get("team") or {}
            team_info = {"id": t.get("id"), "name": t.get("name", "?")}

        loc = _player_location(e, player_id)
        if loc is None:
            continue
        points.append(loc)

        pass_data = e.get("pass") or {}
        rec_id = (pass_data.get("recipient") or {}).get("id")
        if rec_id == player_id and pass_data.get("accurate") and p.get("id") != player_id:
            receptions += 1

    if not points or player_info is None:
        return None

    cells = [[0] * grid_cols for _ in range(grid_rows)]
    for x, y in points:
        col = min(int(x / 100 * grid_cols), grid_cols - 1)
        row = min(int(y / 100 * grid_rows), grid_rows - 1)
        cells[row][col] += 1

    avg_x = sum(x for x, _ in points) / len(points)
    avg_y = sum(y for _, y in points) / len(points)

    zones = {"def_third": 0, "mid_third": 0, "att_third": 0}
    for x, _ in points:
        if x < 100 / 3:
            zones["def_third"] += 1
        elif x < 200 / 3:
            zones["mid_third"] += 1
        else:
            zones["att_third"] += 1

    flanks = {"left": 0, "center": 0, "right": 0}
    for _, y in points:
        if y < 100 / 3:
            flanks["left"] += 1
        elif y < 200 / 3:
            flanks["center"] += 1
        else:
            flanks["right"] += 1

    return {
        "player": player_info,
        "team": team_info,
        "grid": {"cols": grid_cols, "rows": grid_rows, "cells": cells},
        "stats": {
            "total_touches": len(points),
            "avg_x": round(avg_x, 2),
            "avg_y": round(avg_y, 2),
            "zones": zones,
            "flanks": flanks,
            "receptions": receptions,
        },
    }
