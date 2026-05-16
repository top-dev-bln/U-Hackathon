"""Possession-chain analysis logic, extracted as a reusable module.

Originally the body of `possession_chain_analysis.py`. Exposes one top-level
entry point — `analyze_match(events, home_id, away_id)` — that returns the same
JSON shape the offline tool produced (metadata, chains, teamStats, comparison).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timezone

SET_PIECE_TYPES = {"kick_off", "throw_in", "goal_kick", "corner", "free_kick", "penalty"}


def to_float(x, default=0.0):
    if x is None:
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def chain_team_id(chain):
    first = chain[0]
    poss = first.get("possession")
    if poss and poss.get("team"):
        return poss["team"].get("id"), poss["team"].get("name")
    t = first.get("team") or {}
    return t.get("id"), t.get("name")


def group_into_chains(events):
    chains_by_id: dict = {}
    order: list = []
    synthetic_counter = 0
    for ev in events:
        poss = ev.get("possession")
        if poss and poss.get("id") is not None:
            pid = poss["id"]
        else:
            synthetic_counter += 1
            pid = f"synthetic-{synthetic_counter}"
        if pid not in chains_by_id:
            chains_by_id[pid] = []
            order.append(pid)
        chains_by_id[pid].append(ev)
    return [chains_by_id[pid] for pid in order]


def classify_start_trigger(chain, prev_chain):
    first = chain[0]
    poss = first.get("possession") or {}
    ptypes = poss.get("types") or []

    set_piece_hit = next((t for t in ptypes if t in SET_PIECE_TYPES), None)
    if set_piece_hit:
        return {"type": set_piece_hit, "recoveryZone": None, "recoveryMethod": None}

    curr_team_id, _ = chain_team_id(chain)
    if prev_chain is not None:
        prev_team_id, _ = chain_team_id(prev_chain)
        if prev_team_id != curr_team_id:
            start_x = (first.get("location") or {}).get("x", 50.0)
            if start_x >= 66:
                zone = "high"
            elif start_x >= 33:
                zone = "mid"
            else:
                zone = "low"

            method = "loose_ball"
            primary = (first.get("type") or {}).get("primary")
            if primary == "ground_duel":
                gd = first.get("groundDuel") or {}
                if gd.get("won"):
                    method = "tackle_won"
            elif primary == "aerial_duel":
                ad = first.get("aerialDuel") or {}
                if ad.get("won"):
                    method = "aerial_won"
            else:
                last_prev = prev_chain[-1]
                if (last_prev.get("type") or {}).get("primary") == "pass":
                    passd = last_prev.get("pass") or {}
                    if passd.get("accurate") is False:
                        method = "interception"

            return {"type": "recovery", "recoveryZone": zone, "recoveryMethod": method}

    return {"type": "other", "recoveryZone": None, "recoveryMethod": None}


def derive_result(chain):
    last = chain[-1]
    primary = (last.get("type") or {}).get("primary")
    secondary = (last.get("type") or {}).get("secondary") or []
    shot = last.get("shot") or {}
    passd = last.get("pass") or {}

    if primary == "shot":
        if shot.get("isGoal"):
            return "goal"
        if shot.get("onTarget"):
            return "shot_on_target"
        return "shot_off_target"

    if "offside" in secondary:
        return "offside"

    if primary == "infraction":
        return "foul_won"

    if "loss" in secondary or "duel_lost" in secondary:
        return "loss"

    if primary == "pass" and passd.get("accurate") is False:
        return "loss"

    return "out_of_play"


def compute_xg(chain):
    total = 0.0
    for ev in chain:
        shot = ev.get("shot")
        if shot and shot.get("xg") is not None:
            total += to_float(shot.get("xg"))
    return round(total, 4)


def compute_effectiveness(chain_length, progression_x, end_x, xg_total, result):
    length_pts = min(chain_length / 8.0, 1.0) * 20.0
    progression_pts = min(max(progression_x, 0.0) / 80.0, 1.0) * 20.0
    end_zone_pts = (max(0.0, min(end_x, 100.0)) / 100.0) * 15.0
    xg_pts = min(xg_total * 5.0, 1.0) * 20.0

    if result == "goal":
        outcome_pts = 25.0
    elif result == "shot_on_target":
        outcome_pts = 20.0
    elif result == "shot_off_target":
        outcome_pts = 12.0
    elif result == "foul_won":
        outcome_pts = 8.0 if end_x >= 66 else 4.0
    elif result == "offside":
        outcome_pts = 6.0
    elif result == "out_of_play":
        outcome_pts = 3.0
    else:
        outcome_pts = 0.0

    return round(min(length_pts + progression_pts + end_zone_pts + xg_pts + outcome_pts, 100.0), 2)


def condensed_events(chain):
    out = []
    for ev in chain:
        t = ev.get("type") or {}
        entry = {
            "minute": ev.get("minute"),
            "second": ev.get("second"),
            "type": t.get("primary"),
            "secondary": t.get("secondary") or [],
            "playerId": (ev.get("player") or {}).get("id"),
            "playerName": (ev.get("player") or {}).get("name"),
            "location": ev.get("location"),
        }
        passd = ev.get("pass")
        if passd:
            entry["accurate"] = passd.get("accurate")
            entry["passEnd"] = passd.get("endLocation")
        shot = ev.get("shot")
        if shot:
            entry["shot"] = {"onTarget": shot.get("onTarget"), "isGoal": shot.get("isGoal"), "xg": shot.get("xg")}
        out.append(entry)
    return out


def build_chain_object(chain, prev_chain):
    first = chain[0]
    last = chain[-1]
    poss = first.get("possession") or {}
    team_id, team_name = chain_team_id(chain)

    start_loc = first.get("location") or {"x": 0.0, "y": 0.0}
    last_primary = (last.get("type") or {}).get("primary")
    if last_primary == "shot":
        end_loc = last.get("location") or start_loc
    else:
        end_loc = (
            (last.get("pass") or {}).get("endLocation")
            or (last.get("carry") or {}).get("endLocation")
            or last.get("location")
            or (poss.get("endLocation") if poss else None)
            or start_loc
        )

    start_x = to_float(start_loc.get("x"))
    start_y = to_float(start_loc.get("y"))
    end_x = to_float(end_loc.get("x"))
    end_y = to_float(end_loc.get("y"))
    progression_x = round(end_x - start_x, 2)

    start_trigger = classify_start_trigger(chain, prev_chain)
    result = derive_result(chain)
    xg_total = compute_xg(chain)
    chain_length = len(chain)

    effectiveness = compute_effectiveness(chain_length, progression_x, end_x, xg_total, result)

    players_seen = {}
    for ev in chain:
        p = ev.get("player")
        if p and p.get("id") is not None and p["id"] not in players_seen:
            players_seen[p["id"]] = {
                "id": p["id"],
                "name": p.get("name"),
                "position": p.get("position"),
            }

    duration = to_float(poss.get("duration")) if poss else 0.0

    return {
        "chainId": poss.get("id") if poss else None,
        "teamId": team_id,
        "teamName": team_name,
        "chainLength": chain_length,
        "duration": round(duration, 2),
        "startMatchPeriod": first.get("matchPeriod"),
        "startMinute": first.get("minute"),
        "startSecond": first.get("second"),
        "startLocation": {"x": start_x, "y": start_y},
        "endLocation": {"x": end_x, "y": end_y},
        "progressionX": progression_x,
        "startTrigger": start_trigger,
        "result": result,
        "xgTotal": xg_total,
        "playersInvolved": list(players_seen.values()),
        "effectivenessScore": effectiveness,
        "events": condensed_events(chain),
    }


def aggregate_team_stats(team_chains, team_id, team_name):
    if not team_chains:
        return {
            "teamName": team_name,
            "totalChains": 0,
            "avgChainLength": 0.0,
            "medianChainLength": 0,
            "avgDurationSec": 0.0,
            "totalXg": 0.0,
            "avgEffectivenessScore": 0.0,
            "recoveryZoneDistribution": {"high": 0, "mid": 0, "low": 0},
            "recoveryMethodDistribution": {},
            "outcomeDistribution": {},
            "conversionRate": 0.0,
            "highPressRecoveries": 0,
            "topChainsByEffectiveness": [],
        }

    lengths = [c["chainLength"] for c in team_chains]
    durations = [c["duration"] for c in team_chains]
    scores = [c["effectivenessScore"] for c in team_chains]

    recovery_zones = {"high": 0, "mid": 0, "low": 0}
    recovery_methods = defaultdict(int)
    outcomes = defaultdict(int)

    shot_results = {"goal", "shot_on_target", "shot_off_target"}
    shot_count = 0

    for c in team_chains:
        trig = c["startTrigger"]
        zone = trig.get("recoveryZone")
        if zone in recovery_zones:
            recovery_zones[zone] += 1
        method = trig.get("recoveryMethod")
        if method:
            recovery_methods[method] += 1
        outcomes[c["result"]] += 1
        if c["result"] in shot_results:
            shot_count += 1

    top_chains = sorted(team_chains, key=lambda c: c["effectivenessScore"], reverse=True)[:10]
    top_condensed = [
        {
            "chainId": c["chainId"],
            "chainLength": c["chainLength"],
            "startMinute": c["startMinute"],
            "startMatchPeriod": c["startMatchPeriod"],
            "result": c["result"],
            "xgTotal": c["xgTotal"],
            "effectivenessScore": c["effectivenessScore"],
            "startTrigger": c["startTrigger"],
        }
        for c in top_chains
    ]

    return {
        "teamName": team_name,
        "totalChains": len(team_chains),
        "avgChainLength": round(statistics.mean(lengths), 2),
        "medianChainLength": int(statistics.median(lengths)),
        "avgDurationSec": round(statistics.mean(durations), 2),
        "totalXg": round(sum(c["xgTotal"] for c in team_chains), 3),
        "avgEffectivenessScore": round(statistics.mean(scores), 2),
        "recoveryZoneDistribution": recovery_zones,
        "recoveryMethodDistribution": dict(recovery_methods),
        "outcomeDistribution": dict(outcomes),
        "conversionRate": round(shot_count / len(team_chains), 4),
        "highPressRecoveries": recovery_zones["high"],
        "topChainsByEffectiveness": top_condensed,
    }


def _advantage(v_a, v_b, team_a, team_b, higher_is_better=True, precision=3):
    a = round(v_a, precision)
    b = round(v_b, precision)
    if a == b:
        return "tie"
    if higher_is_better:
        return team_a if a > b else team_b
    return team_a if a < b else team_b


def build_comparison(stats_by_team, team_a, team_b):
    a = stats_by_team[team_a]
    b = stats_by_team[team_b]
    return {
        "totalChains": {
            str(team_a): a["totalChains"],
            str(team_b): b["totalChains"],
            "advantage": _advantage(a["totalChains"], b["totalChains"], team_a, team_b),
        },
        "avgChainLength": {
            str(team_a): a["avgChainLength"],
            str(team_b): b["avgChainLength"],
            "advantage": _advantage(a["avgChainLength"], b["avgChainLength"], team_a, team_b),
        },
        "avgEffectiveness": {
            str(team_a): a["avgEffectivenessScore"],
            str(team_b): b["avgEffectivenessScore"],
            "advantage": _advantage(a["avgEffectivenessScore"], b["avgEffectivenessScore"], team_a, team_b),
        },
        "totalXg": {
            str(team_a): a["totalXg"],
            str(team_b): b["totalXg"],
            "advantage": _advantage(a["totalXg"], b["totalXg"], team_a, team_b),
        },
        "highPressRecoveries": {
            str(team_a): a["highPressRecoveries"],
            str(team_b): b["highPressRecoveries"],
            "advantage": _advantage(a["highPressRecoveries"], b["highPressRecoveries"], team_a, team_b),
        },
        "conversionRate": {
            str(team_a): a["conversionRate"],
            str(team_b): b["conversionRate"],
            "advantage": _advantage(a["conversionRate"], b["conversionRate"], team_a, team_b),
            "note": "chains ending in shot (on/off target or goal) / total chains",
        },
    }


def analyze_match(events, home_id, away_id, *, match_id=None, scoring_model="v1"):
    """Top-level entry point used by both the offline CLI and the live service."""
    chains_raw = group_into_chains(events)

    chain_objs = []
    prev = None
    for c in chains_raw:
        chain_objs.append(build_chain_object(c, prev))
        prev = c

    chains_by_team: dict = defaultdict(list)
    team_names: dict = {}
    for co in chain_objs:
        tid = co["teamId"]
        if tid is None:
            continue
        chains_by_team[tid].append(co)
        if co["teamName"]:
            team_names[tid] = co["teamName"]

    if home_id is None or away_id is None:
        ids = sorted(chains_by_team.keys())
        if not ids:
            home_id = away_id = None
        elif len(ids) == 1:
            home_id = away_id = ids[0]
        else:
            home_id, away_id = ids[0], ids[1]

    stats_by_team = {
        tid: aggregate_team_stats(
            chains_by_team.get(tid, []), tid, team_names.get(tid, str(tid))
        )
        for tid in (home_id, away_id) if tid is not None
    }

    comparison = (
        build_comparison(stats_by_team, home_id, away_id)
        if home_id is not None and away_id is not None and home_id != away_id
        else {}
    )

    return {
        "metadata": {
            "matchId": match_id,
            "homeTeam": {"id": home_id, "name": team_names.get(home_id, str(home_id))},
            "awayTeam": {"id": away_id, "name": team_names.get(away_id, str(away_id))},
            "totalEvents": len(events),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "scoringModel": scoring_model,
        },
        "chains": {
            str(home_id): chains_by_team.get(home_id, []),
            str(away_id): chains_by_team.get(away_id, []),
        },
        "teamStats": {
            str(home_id): stats_by_team.get(home_id, {}),
            str(away_id): stats_by_team.get(away_id, {}),
        },
        "comparison": comparison,
    }
