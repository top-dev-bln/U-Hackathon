"""Detect and aggregate line-breaking passes for a team in a match.

Definition:
- A line-breaking pass = a pass tagged by Wyscout's secondary types as either
  `progressive_pass` (significant forward progression) OR `through_pass`
  (passes between defensive lines / behind the back line).
- Both completed and incomplete attempts are counted; completion_rate is a
  separate metric. Coaches care about both intent (attempts) and execution.
"""

from collections import defaultdict
from typing import Any

PROGRESSIVE = "progressive_pass"
THROUGH = "through_pass"


def _filter_period(events: list[dict], period: str) -> list[dict]:
    if period == "full":
        return events
    return [e for e in events if e.get("matchPeriod") == period]


def _zone(x: float | None) -> str:
    if x is None:
        return "middle_third"
    if x < 100 / 3:
        return "defensive_third"
    if x < 200 / 3:
        return "middle_third"
    return "attacking_third"


def build_line_breaks(
    events: list[dict[str, Any]],
    team_id: int,
    period: str = "full",
) -> dict:
    filtered = _filter_period(events, period)

    line_events: list[dict] = []
    by_type: dict[str, int] = defaultdict(int)
    by_target_zone: dict[str, int] = defaultdict(int)
    player_stats: dict[int, dict] = {}

    for e in filtered:
        team = (e.get("team") or {}).get("id")
        if team != team_id:
            continue
        typ = e.get("type") or {}
        if typ.get("primary") != "pass":
            continue
        secondary = typ.get("secondary") or []
        is_progressive = PROGRESSIVE in secondary
        is_through = THROUGH in secondary
        if not (is_progressive or is_through):
            continue

        # "through" wins if both tags present (rarer + more telling)
        kind = "through" if is_through else "progressive"

        pass_data = e.get("pass") or {}
        accurate = bool(pass_data.get("accurate"))

        loc = e.get("location") or {}
        end = pass_data.get("endLocation") or {}
        start_x = loc.get("x")
        start_y = loc.get("y")
        end_x = end.get("x")
        end_y = end.get("y")

        target_zone = _zone(end_x)
        by_type[kind] += 1
        by_target_zone[target_zone] += 1

        passer = e.get("player") or {}
        recipient = pass_data.get("recipient") or {}

        pid = passer.get("id")
        if pid:
            slot = player_stats.setdefault(
                pid,
                {
                    "id": pid,
                    "name": passer.get("name", "?"),
                    "position": passer.get("position"),
                    "attempts": 0,
                    "completed": 0,
                },
            )
            slot["attempts"] += 1
            if accurate:
                slot["completed"] += 1

        line_events.append(
            {
                "minute": e.get("minute", 0),
                "second": e.get("second", 0),
                "period": e.get("matchPeriod"),
                "type": kind,
                "accurate": accurate,
                "passer_id": pid,
                "passer_name": passer.get("name"),
                "passer_position": passer.get("position"),
                "recipient_id": recipient.get("id"),
                "recipient_name": recipient.get("name"),
                "recipient_position": recipient.get("position"),
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "length": pass_data.get("length"),
                "target_zone": target_zone,
            }
        )

    total = len(line_events)
    completed = sum(1 for r in line_events if r["accurate"])
    completion_rate = round(completed / total, 3) if total else 0.0

    by_player_list = []
    for slot in player_stats.values():
        rate = round(slot["completed"] / slot["attempts"], 3) if slot["attempts"] else 0.0
        by_player_list.append({**slot, "completion_rate": rate})
    by_player_list.sort(key=lambda p: (p["attempts"], p["completed"]), reverse=True)

    return {
        "total_attempts": total,
        "total_completed": completed,
        "completion_rate": completion_rate,
        "by_type": dict(by_type),
        "by_target_zone": dict(by_target_zone),
        "by_player": by_player_list,
        "events": line_events,
    }
