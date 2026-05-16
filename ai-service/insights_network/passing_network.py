from collections import defaultdict
from typing import Any


def _first_sub_minute(substitutions: dict, team_id: int) -> int | None:
    team_subs = (substitutions or {}).get(str(team_id), {})
    minutes: list[int] = []
    for period_subs in team_subs.values():
        for sub in period_subs:
            if "minute" in sub:
                minutes.append(sub["minute"])
    return min(minutes) if minutes else None


def _absolute_minute(event: dict) -> int:
    m = event.get("minute", 0)
    return m + 45 if event.get("matchPeriod") == "2H" else m


def build_passing_network(
    events: list[dict[str, Any]],
    team_id: int,
    substitutions: dict | None = None,
    period: str = "full",
    until_first_sub: bool = True,
    min_passes: int = 2,
    accurate_only: bool = True,
) -> dict:
    cutoff_minute = _first_sub_minute(substitutions or {}, team_id) if until_first_sub else None

    def in_window(e: dict) -> bool:
        if (e.get("team") or {}).get("id") != team_id:
            return False
        if period in ("1H", "2H") and e.get("matchPeriod") != period:
            return False
        if cutoff_minute is not None and _absolute_minute(e) >= cutoff_minute:
            return False
        return True

    relevant = [e for e in events if in_window(e)]

    player_info: dict[int, dict] = {}
    player_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    touches: dict[int, int] = defaultdict(int)

    for e in relevant:
        p = e.get("player") or {}
        pid = p.get("id")
        if pid is None:
            continue
        player_info.setdefault(pid, {"name": p.get("name", "?"), "position": p.get("position", "?")})
        loc = e.get("location") or {}
        if loc.get("x") is not None and loc.get("y") is not None:
            player_locs[pid].append((loc["x"], loc["y"]))
        touches[pid] += 1

    edge_counts: dict[tuple[int, int], int] = defaultdict(int)
    for e in relevant:
        if (e.get("type") or {}).get("primary") != "pass":
            continue
        passer = (e.get("player") or {}).get("id")
        pass_data = e.get("pass") or {}
        recipient = (pass_data.get("recipient") or {}).get("id")
        if not passer or not recipient:
            continue
        if accurate_only and not pass_data.get("accurate", False):
            continue
        edge_counts[(passer, recipient)] += 1

    nodes_out = []
    for pid, info in player_info.items():
        locs = player_locs.get(pid, [])
        if not locs:
            continue
        avg_x = sum(x for x, _ in locs) / len(locs)
        avg_y = sum(y for _, y in locs) / len(locs)
        nodes_out.append(
            {
                "id": pid,
                "name": info["name"],
                "position": info["position"],
                "x": round(avg_x, 2),
                "y": round(avg_y, 2),
                "touches": touches[pid],
            }
        )

    nodes_out.sort(key=lambda n: n["touches"], reverse=True)

    edges_out = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in edge_counts.items()
        if w >= min_passes
    ]
    edges_out.sort(key=lambda e: e["weight"], reverse=True)

    return {"nodes": nodes_out, "edges": edges_out, "cutoff_minute": cutoff_minute}
