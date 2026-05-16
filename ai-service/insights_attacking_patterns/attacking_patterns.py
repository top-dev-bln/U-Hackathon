from collections import defaultdict


def _filter_by_period(events: list[dict], period: str) -> list[dict]:
    if period == "full":
        return events
    return [e for e in events if e.get("matchPeriod") == period]


def _build_insight(flank_counts: dict, total: int, avg_xg: float, attack_types: list[dict]) -> str:
    if total == 0:
        return "No attacking sequences recorded."

    # Dominant flank
    dominant = max(flank_counts, key=flank_counts.get)
    flank_label = {"left": "left flank", "right": "right flank", "center": "central channel"}[dominant]

    parts = [f"Attack primarily built through the {flank_label}"]

    # Most dangerous attack type
    if attack_types:
        top = max(attack_types, key=lambda a: a["xgTotal"])
        if top["xgTotal"] > 0:
            parts.append(f"most danger from {top['label'].replace('_', ' ')} attacks (xG {top['xgTotal']:.2f})")

    if avg_xg >= 0.15:
        parts.append("high quality chances created per attack")
    elif avg_xg >= 0.07:
        parts.append("moderate chance quality")
    else:
        parts.append("low xG per attack — final ball needs improvement")

    return ", ".join(parts) + "."


def build_attacking_patterns(
    events: list[dict],
    team_id: int,
    period: str = "full",
) -> dict:
    filtered = _filter_by_period(events, period)

    # Group by possession id to analyse full attacks
    possessions: dict[int, dict] = {}

    for event in filtered:
        if event["team"]["id"] != team_id:
            continue

        poss = event.get("possession") or {}
        poss_id = poss.get("id")
        if poss_id is None:
            continue

        attack_info = poss.get("attack") or {}
        if not attack_info:
            continue

        if poss_id not in possessions:
            possessions[poss_id] = {
                "flank": attack_info.get("flank", "center"),
                "withShot": attack_info.get("withShot", False),
                "withGoal": attack_info.get("withGoal", False),
                "withShotOnGoal": attack_info.get("withShotOnGoal", False),
                "xg": attack_info.get("xg", 0.0),
                "types": poss.get("types", []),
                "players": set(),
            }

        possessions[poss_id]["players"].add(event["player"]["id"])
        possessions[poss_id]["_player_name"] = event["player"]["name"]
        possessions[poss_id]["_player_pos"] = event["player"].get("position")
        possessions[poss_id]["_player_id"] = event["player"]["id"]

    # Aggregate per flank
    flank_counts = {"left": 0, "center": 0, "right": 0}
    attack_type_stats: dict[str, dict] = {}
    player_stats: dict[int, dict] = defaultdict(lambda: {
        "name": "", "position": None, "attacks": 0, "shots": 0,
        "xg": 0.0, "flank_counter": defaultdict(int),
    })

    total_xg = 0.0

    for poss in possessions.values():
        flank = poss["flank"] if poss["flank"] in flank_counts else "center"
        flank_counts[flank] += 1
        total_xg += poss["xg"]

        # Attack types (transition_low, transition_high, positional, etc.)
        for t in poss["types"]:
            if t not in attack_type_stats:
                attack_type_stats[t] = {"label": t, "count": 0, "withShot": 0, "withGoal": 0, "xgTotal": 0.0}
            attack_type_stats[t]["count"] += 1
            attack_type_stats[t]["xgTotal"] += poss["xg"]
            if poss["withShot"]:
                attack_type_stats[t]["withShot"] += 1
            if poss["withGoal"]:
                attack_type_stats[t]["withGoal"] += 1

        # Per player (last player in possession)
        pid = poss.get("_player_id")
        if pid:
            player_stats[pid]["name"] = poss.get("_player_name", "")
            player_stats[pid]["position"] = poss.get("_player_pos")
            player_stats[pid]["attacks"] += 1
            player_stats[pid]["xg"] += poss["xg"]
            player_stats[pid]["flank_counter"][flank] += 1
            if poss["withShot"]:
                player_stats[pid]["shots"] += 1

    total_attacks = len(possessions)
    avg_xg = round(total_xg / total_attacks, 3) if total_attacks > 0 else 0.0
    most_dangerous_flank = max(flank_counts, key=flank_counts.get) if total_attacks > 0 else "center"

    attack_types_list = sorted(attack_type_stats.values(), key=lambda a: a["count"], reverse=True)
    for at in attack_types_list:
        at["xgTotal"] = round(at["xgTotal"], 3)

    players = []
    for pid, s in player_stats.items():
        if s["attacks"] == 0:
            continue
        preferred_flank = max(s["flank_counter"], key=s["flank_counter"].get) if s["flank_counter"] else None
        players.append({
            "id": pid,
            "name": s["name"],
            "position": s["position"],
            "attacks": s["attacks"],
            "shots": s["shots"],
            "xgCreated": round(s["xg"], 3),
            "preferredFlank": preferred_flank,
        })

    players.sort(key=lambda p: (p["xgCreated"], p["attacks"]), reverse=True)

    return {
        "totalAttacks": total_attacks,
        "flankBreakdown": flank_counts,
        "attackTypes": attack_types_list,
        "avgXgPerAttack": avg_xg,
        "mostDangerousFlank": most_dangerous_flank,
        "insight": _build_insight(flank_counts, total_attacks, avg_xg, attack_types_list),
        "players": players,
        "topAttacker": players[0]["name"] if players else None,
    }
