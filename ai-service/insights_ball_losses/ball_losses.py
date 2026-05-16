"""Detect and aggregate ball losses for a team in a match.

Definition (aligned across services):
- A ball loss is the *event* at which the team gave up possession through its
  own action. Detected via Wyscout's own annotation on the event:
    * primary == "pass" and pass.accurate is False
    * "loss" in secondary
    * "duel_lost" in secondary
- NOT a ball loss: shots, offsides, fouls, end-of-half / out-of-play.
- Each loss is classified by zone (where it happened), giving a danger axis.
"""

from collections import defaultdict
from typing import Any

GRID_COLS = 12
GRID_ROWS = 8


def _filter_period(events: list[dict], period: str) -> list[dict]:
    if period == "full":
        return events
    return [e for e in events if e.get("matchPeriod") == period]


def _zone(end_x: float | None) -> str:
    if end_x is None:
        return "middle_third"
    if end_x < 100 / 3:
        return "defensive_third"
    if end_x < 200 / 3:
        return "middle_third"
    return "attacking_third"


def _classify_loss(event: dict) -> str | None:
    """Return loss type string if this event is a ball loss for the actor's team, else None."""
    typ = event.get("type") or {}
    primary = typ.get("primary")
    secondary = typ.get("secondary") or []

    # Explicit loss tag
    if "loss" in secondary:
        return "loss_tag"
    # Lost duel
    if "duel_lost" in secondary:
        return "duel_lost"
    # Inaccurate pass
    if primary == "pass":
        pass_data = event.get("pass") or {}
        if pass_data.get("accurate") is False:
            return "inaccurate_pass"
    return None


def build_ball_losses(
    events: list[dict[str, Any]],
    team_id: int,
    period: str = "full",
) -> dict:
    filtered = _filter_period(events, period)

    loss_events: list[dict] = []
    by_zone: dict[str, int] = {"defensive_third": 0, "middle_third": 0, "attacking_third": 0}
    by_type: dict[str, int] = defaultdict(int)
    player_losses: dict[int, dict] = {}

    cells = [[0] * GRID_COLS for _ in range(GRID_ROWS)]

    for e in filtered:
        team = (e.get("team") or {}).get("id")
        if team != team_id:
            continue
        loss_type = _classify_loss(e)
        if loss_type is None:
            continue

        loc = e.get("location") or {}
        x = loc.get("x")
        y = loc.get("y")
        zone = _zone(x)
        by_zone[zone] += 1
        by_type[loss_type] += 1

        if x is not None and y is not None:
            col = min(int(x / 100 * GRID_COLS), GRID_COLS - 1)
            row = min(int(y / 100 * GRID_ROWS), GRID_ROWS - 1)
            cells[row][col] += 1

        player = e.get("player") or {}
        pid = player.get("id")
        if pid:
            slot = player_losses.setdefault(
                pid,
                {
                    "id": pid,
                    "name": player.get("name", "?"),
                    "position": player.get("position"),
                    "losses": 0,
                    "dangerous_losses": 0,
                },
            )
            slot["losses"] += 1
            if zone == "defensive_third":
                slot["dangerous_losses"] += 1

        loss_events.append(
            {
                "minute": e.get("minute", 0),
                "second": e.get("second", 0),
                "period": e.get("matchPeriod"),
                "player_id": pid,
                "player_name": player.get("name"),
                "player_position": player.get("position"),
                "x": x,
                "y": y,
                "zone": zone,
                "type": loss_type,
            }
        )

    total = len(loss_events)
    danger_score = 0.0
    if total:
        danger_score = round(
            (
                by_zone["defensive_third"] * 3.0
                + by_zone["middle_third"] * 1.0
                + by_zone["attacking_third"] * 0.3
            )
            / total,
            3,
        )

    by_player_sorted = sorted(
        player_losses.values(),
        key=lambda p: (p["dangerous_losses"], p["losses"]),
        reverse=True,
    )

    return {
        "total_losses": total,
        "by_zone": by_zone,
        "by_type": dict(by_type),
        "by_player": by_player_sorted,
        "grid": {"cols": GRID_COLS, "rows": GRID_ROWS, "cells": cells},
        "danger_score": danger_score,
        "events": loss_events,
    }
