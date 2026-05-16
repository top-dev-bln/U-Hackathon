#!/usr/bin/env python3
"""Possession Chain Analysis CLI — thin wrapper that loads a Wyscout JSON file
and runs the live analyzer offline against it. The actual logic lives in
`stats_service/analyzer.py` (single source of truth shared with the live
microservice).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stats_service import analyzer


def load_events(path: Path):
    with path.open() as f:
        doc = json.load(f)
    elements = doc["elements"][0]
    events = elements["events"]
    match = elements.get("match", {})
    teams = elements.get("teams", {})
    meta = doc.get("meta", {})
    return events, match, teams, meta


def render_stdout_summary(output):
    md = output["metadata"]
    home = md["homeTeam"]
    away = md["awayTeam"]
    stats = output["teamStats"]
    comp = output.get("comparison") or {}

    print()
    print("=" * 72)
    print(f"  Possession Chain Analysis — Match {md['matchId']}")
    print(f"  {home['name']} (id {home['id']})  vs  {away['name']} (id {away['id']})")
    print(f"  Total events: {md['totalEvents']}  |  Generated: {md['generatedAt']}")
    print("=" * 72)

    if not comp:
        print("  (insufficient data for head-to-head comparison)")
        return

    def lbl(adv, tid):
        if adv == "tie":
            return "  "
        return "* " if adv == tid else "  "

    def row(label, key, fmt="{}"):
        va = comp[key][str(home["id"])]
        vb = comp[key][str(away["id"])]
        adv = comp[key]["advantage"]
        print(f"  {label:<26} {lbl(adv, home['id'])}{fmt.format(va):>12}  |  {fmt.format(vb):>12}{lbl(adv, away['id'])}")

    print()
    print(f"  {'Metric':<26}   {home['name']:>12}  |  {away['name']:>12}")
    print("  " + "-" * 68)
    row("Total chains", "totalChains")
    row("Avg chain length", "avgChainLength", "{:.2f}")
    row("Avg effectiveness", "avgEffectiveness", "{:.2f}")
    row("Total xG", "totalXg", "{:.3f}")
    row("High-press recoveries", "highPressRecoveries")
    row("Conversion rate", "conversionRate", "{:.3f}")

    for team_info in (home, away):
        tid = str(team_info["id"])
        s = stats[tid]
        print()
        print(f"  === {team_info['name']} — Recovery Zones ===")
        rz = s["recoveryZoneDistribution"]
        print(f"    high (x>=66): {rz['high']:>3}   mid (33-66): {rz['mid']:>3}   low (<33): {rz['low']:>3}")
        print(f"  === Recovery Methods ===")
        for k, v in sorted(s["recoveryMethodDistribution"].items(), key=lambda kv: -kv[1]):
            print(f"    {k:<16} {v:>3}")
        print(f"  === Outcomes ===")
        for k, v in sorted(s["outcomeDistribution"].items(), key=lambda kv: -kv[1]):
            print(f"    {k:<18} {v:>3}")
        print(f"  === Top 3 Chains by Effectiveness ===")
        for c in s["topChainsByEffectiveness"][:3]:
            trig = c["startTrigger"]
            trig_str = trig["type"]
            if trig["type"] == "recovery":
                trig_str = f"recovery/{trig['recoveryZone']}/{trig['recoveryMethod']}"
            print(
                f"    chain {c['chainId']}  min {c['startMatchPeriod']} {c['startMinute']:>2}'  "
                f"len={c['chainLength']}  xG={c['xgTotal']:.3f}  "
                f"result={c['result']:<16}  score={c['effectivenessScore']:>6.2f}  [{trig_str}]"
            )
    print()
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Possession Chain Analysis (offline CLI)")
    parser.add_argument("--input", "-i", required=True, type=Path, help="Wyscout events JSON")
    parser.add_argument("--output", "-o", required=True, type=Path, help="Output JSON path")
    parser.add_argument("--no-summary", action="store_true", help="Suppress stdout summary")
    args = parser.parse_args()

    events, match, _teams, meta = load_events(args.input)

    home_id = match.get("teamsData", {}).get("home", {}).get("teamId")
    away_id = match.get("teamsData", {}).get("away", {}).get("teamId")
    match_id = match.get("wyId") or match.get("matchId")

    output = analyzer.analyze_match(events, home_id, away_id, match_id=match_id)
    output["metadata"]["totalEvents"] = meta.get("count", len(events))

    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    if not args.no_summary:
        render_stdout_summary(output)
        print(f"  Full JSON written to: {args.output}")
        print()


if __name__ == "__main__":
    main()
