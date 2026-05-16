from collections import defaultdict

# Thresholds
FINAL_THIRD_X = 66.0   # entering opponent's final third
BOX_X = 83.0           # entering penalty box area
BOX_Y_MIN = 21.1
BOX_Y_MAX = 78.9
MIN_PROGRESSION_X = 10.0  # minimum x gain to count as line-breaking carry


def _filter_by_period(events: list[dict], period: str) -> list[dict]:
    if period == "full":
        return events
    return [e for e in events if e.get("matchPeriod") == period]


def _in_box(x: float, y: float) -> bool:
    return x >= BOX_X and BOX_Y_MIN <= y <= BOX_Y_MAX


def _builds_insight(total: int, into_box: int, led_to_shot: int) -> str:
    parts = []
    if total == 0:
        return "No line-breaking actions recorded."
    if into_box >= 5:
        parts.append(f"Dangerous line-breaking threat — {into_box} runs reached the box")
    elif into_box >= 2:
        parts.append(f"Moderate penetration — {into_box} runs into the box")
    else:
        parts.append("Limited box penetration from progressive runs")

    if led_to_shot > 0:
        parts.append(f"{led_to_shot} run(s) directly created a shot")
    else:
        parts.append("none led directly to a shot")

    return ", ".join(parts) + "."


def build_line_breaking_runs(
    events: list[dict],
    team_id: int,
    period: str = "full",
) -> dict:
    filtered = _filter_by_period(events, period)

    stats = defaultdict(lambda: {
        "name": "",
        "position": None,
        "progressive_carries": 0,
        "progressive_passes": 0,
        "progression_x_total": 0.0,
        "progression_x_count": 0,
        "into_final_third": 0,
        "into_box": 0,
        "led_to_shot": 0,
    })

    totals = {
        "progressive_carries": 0,
        "progressive_passes": 0,
        "into_final_third": 0,
        "into_box": 0,
        "led_to_shot": 0,
    }

    # Build a quick index of what follows each event (to check led_to_shot)
    event_ids = [e["id"] for e in filtered]
    event_index = {e["id"]: i for i, e in enumerate(filtered)}

    for i, event in enumerate(filtered):
        if event["team"]["id"] != team_id:
            continue

        pid = event["player"]["id"]
        ptype = event["type"]["primary"]
        secondary = event["type"].get("secondary", [])

        stats[pid]["name"] = event["player"]["name"]
        stats[pid]["position"] = event["player"].get("position")

        # --- Progressive carry ---
        if ptype == "carry" and "progressive_carry" in secondary:
            carry = event.get("carry") or {}
            start_x = event["location"]["x"]
            end_x = carry.get("endLocation", {}).get("x", start_x)
            end_y = carry.get("endLocation", {}).get("y", 50)
            progression = end_x - start_x

            if progression >= MIN_PROGRESSION_X:
                stats[pid]["progressive_carries"] += 1
                stats[pid]["progression_x_total"] += progression
                stats[pid]["progression_x_count"] += 1
                totals["progressive_carries"] += 1

                if end_x >= FINAL_THIRD_X:
                    stats[pid]["into_final_third"] += 1
                    totals["into_final_third"] += 1

                if _in_box(end_x, end_y):
                    stats[pid]["into_box"] += 1
                    totals["into_box"] += 1

                # Check if next event by same team is a shot
                for j in range(i + 1, min(i + 4, len(filtered))):
                    next_e = filtered[j]
                    if next_e["team"]["id"] != team_id:
                        break
                    if next_e["type"]["primary"] == "shot":
                        stats[pid]["led_to_shot"] += 1
                        totals["led_to_shot"] += 1
                        break

        # --- Progressive pass (line-breaking) ---
        elif ptype == "pass" and "progressive_pass" in secondary:
            p_data = event.get("pass") or {}
            start_x = event["location"]["x"]
            end_x = p_data.get("endLocation", {}).get("x", start_x)
            end_y = p_data.get("endLocation", {}).get("y", 50)
            progression = end_x - start_x
            accurate = p_data.get("accurate", False)

            if accurate and progression >= MIN_PROGRESSION_X:
                stats[pid]["progressive_passes"] += 1
                stats[pid]["progression_x_total"] += progression
                stats[pid]["progression_x_count"] += 1
                totals["progressive_passes"] += 1

                if end_x >= FINAL_THIRD_X:
                    stats[pid]["into_final_third"] += 1
                    totals["into_final_third"] += 1

                if _in_box(end_x, end_y):
                    stats[pid]["into_box"] += 1
                    totals["into_box"] += 1

                for j in range(i + 1, min(i + 4, len(filtered))):
                    next_e = filtered[j]
                    if next_e["team"]["id"] != team_id:
                        break
                    if next_e["type"]["primary"] == "shot":
                        stats[pid]["led_to_shot"] += 1
                        totals["led_to_shot"] += 1
                        break

    players = []
    for pid, s in stats.items():
        total_runs = s["progressive_carries"] + s["progressive_passes"]
        if total_runs == 0:
            continue
        avg_prog = round(s["progression_x_total"] / s["progression_x_count"], 1) if s["progression_x_count"] > 0 else 0.0
        players.append({
            "id": pid,
            "name": s["name"],
            "position": s["position"],
            "totalRuns": total_runs,
            "progressiveCarries": s["progressive_carries"],
            "progressivePasses": s["progressive_passes"],
            "avgProgressionX": avg_prog,
            "intoFinalThird": s["into_final_third"],
            "intoBox": s["into_box"],
            "led_to_shot": s["led_to_shot"],
        })

    players.sort(key=lambda p: (p["intoBox"], p["totalRuns"]), reverse=True)
    total_actions = totals["progressive_carries"] + totals["progressive_passes"]

    return {
        "totalLineBreakingActions": total_actions,
        "progressiveCarries": totals["progressive_carries"],
        "progressivePasses": totals["progressive_passes"],
        "intoFinalThird": totals["into_final_third"],
        "intoBox": totals["into_box"],
        "led_to_shot": totals["led_to_shot"],
        "insight": _builds_insight(total_actions, totals["into_box"], totals["led_to_shot"]),
        "players": players,
        "topRunner": players[0]["name"] if players else None,
    }
