from collections import defaultdict


def _efficiency(won: int, total: int) -> float:
    return round(won / total, 2) if total > 0 else 0.0


def _build_insight(team_eff: float, drop: float) -> str:
    parts = []

    if team_eff >= 0.65:
        parts.append("Strong pressing performance overall")
    elif team_eff >= 0.50:
        parts.append("Moderate pressing efficiency")
    else:
        parts.append("Pressing was largely ineffective")

    if abs(drop) < 0.05:
        parts.append("consistent intensity across both halves")
    elif drop <= -0.15:
        parts.append(f"significant drop in the second half ({abs(drop):.0%} less effective)")
    elif drop <= -0.05:
        parts.append("slight decline in the second half")
    else:
        parts.append("pressing improved in the second half")

    return ", ".join(parts) + "."


def _filter_by_period(events: list[dict], period: str) -> list[dict]:
    if period == "full":
        return events
    return [e for e in events if e.get("matchPeriod") == period]


def build_pressing(
    events: list[dict],
    team_id: int,
    period: str = "full",
) -> dict:
    filtered = _filter_by_period(events, period)

    stats = defaultdict(lambda: {
        "name": "", "position": None,
        "1H": {"duels": 0, "won": 0},
        "2H": {"duels": 0, "won": 0},
        "opp_half": 0,
    })
    team_duels = {
        "1H": {"duels": 0, "won": 0},
        "2H": {"duels": 0, "won": 0},
    }

    for event in filtered:
        if event["team"]["id"] != team_id:
            continue
        if event["type"]["primary"] not in ("ground_duel", "aerial_duel"):
            continue

        sec  = event["type"]["secondary"]
        pid  = event["player"]["id"]
        half = event["matchPeriod"] if event["matchPeriod"] in ("1H", "2H") else "2H"
        won  = "duel_won" in sec

        stats[pid]["name"]     = event["player"]["name"]
        stats[pid]["position"] = event["player"].get("position")
        stats[pid][half]["duels"] += 1
        stats[pid]["opp_half"] += 1 if event["location"]["x"] > 66 else 0

        if won:
            stats[pid][half]["won"] += 1

        team_duels[half]["duels"] += 1
        if won:
            team_duels[half]["won"] += 1

    first_eff  = _efficiency(team_duels["1H"]["won"], team_duels["1H"]["duels"])
    second_eff = _efficiency(team_duels["2H"]["won"], team_duels["2H"]["duels"])
    total_won  = team_duels["1H"]["won"]   + team_duels["2H"]["won"]
    total      = team_duels["1H"]["duels"] + team_duels["2H"]["duels"]
    team_eff   = _efficiency(total_won, total)
    drop       = round(second_eff - first_eff, 2)

    players = []
    for pid, s in stats.items():
        p1h = s["1H"]["duels"]
        p2h = s["2H"]["duels"]
        if p1h + p2h == 0:
            continue

        eff_1h  = _efficiency(s["1H"]["won"], p1h)
        eff_2h  = _efficiency(s["2H"]["won"], p2h)
        eff_tot = _efficiency(s["1H"]["won"] + s["2H"]["won"], p1h + p2h)
        p_drop  = round(eff_2h - eff_1h, 2) if p1h > 0 and p2h > 0 else 0.0

        players.append({
            "id":             pid,
            "name":           s["name"],
            "position":       s["position"],
            "pressingDuels":  p1h + p2h,
            "won":            s["1H"]["won"] + s["2H"]["won"],
            "efficiency":     eff_tot,
            "inOpponentHalf": s["opp_half"],
            "intensityDrop":  p_drop,
        })

    players.sort(key=lambda p: (p["efficiency"], p["pressingDuels"]), reverse=True)

    return {
        "teamPressingEfficiency": team_eff,
        "firstHalfEfficiency":    first_eff,
        "secondHalfEfficiency":   second_eff,
        "intensityDrop":          drop,
        "insight":                _build_insight(team_eff, drop),
        "players":                players,
        "topPresser":             players[0]["name"] if players else None,
    }
