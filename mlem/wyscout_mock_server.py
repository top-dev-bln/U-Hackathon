#!/usr/bin/env python3
"""Wyscout mock HTTP server — simulates live match feed by replaying events
from a static JSON file at a configurable speed. Returns cumulative snapshots
(not deltas) so downstream dedup (Redis) is exercised.

Endpoints:
  GET  /events           — cumulative events up to simulated match time
  POST /control/reset    — reset T0 (simulation restarts at 0:00)
  POST /control/speed    — body {"multiplier": 10}
  GET  /control/status   — simulatedMinute/Second, events drained, T0, multiplier
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def load_match(path: Path):
    with path.open() as f:
        doc = json.load(f)
    elements = doc["elements"][0]
    events_raw = elements["events"]
    match_raw = elements.get("match", {})
    teams_raw = elements.get("teams", {})

    home_id = match_raw.get("teamsData", {}).get("home", {}).get("teamId")
    away_id = match_raw.get("teamsData", {}).get("away", {}).get("teamId")
    if home_id is None or away_id is None:
        seen = []
        for ev in events_raw:
            tid = (ev.get("team") or {}).get("id")
            if tid and tid not in seen:
                seen.append(tid)
            if len(seen) == 2:
                break
        home_id = home_id or (seen[0] if seen else None)
        away_id = away_id or (seen[1] if len(seen) > 1 else None)

    def team_name(tid):
        t = teams_raw.get(str(tid)) or teams_raw.get(tid) or {}
        return t.get("officialName") or t.get("name") or str(tid)

    label = f"{team_name(home_id)} - {team_name(away_id)}"

    match_meta = {
        "wyId": match_raw.get("wyId") or match_raw.get("matchId"),
        "label": label,
        "homeTeamId": home_id,
        "awayTeamId": away_id,
    }

    events = [slim_event(ev) for ev in events_raw]
    events.sort(key=lambda e: (0 if e.get("matchPeriod") == "1H" else 1,
                               e.get("minute") or 0,
                               e.get("second") or 0,
                               e.get("id") or 0))
    return match_meta, events


def slim_event(ev):
    """Project a Wyscout event down to just the fields downstream consumers use."""
    out = {
        "id": ev.get("id"),
        "matchId": ev.get("matchId"),
        "matchPeriod": ev.get("matchPeriod"),
        "minute": ev.get("minute"),
        "second": ev.get("second"),
        "type": {
            "primary": (ev.get("type") or {}).get("primary"),
            "secondary": (ev.get("type") or {}).get("secondary") or [],
        },
        "location": ev.get("location"),
    }
    team = ev.get("team") or {}
    if team:
        out["team"] = {"id": team.get("id"), "name": team.get("name")}
    player = ev.get("player") or {}
    if player:
        out["player"] = {
            "id": player.get("id"),
            "name": player.get("name"),
            "position": player.get("position"),
        }

    passd = ev.get("pass")
    if passd:
        recipient = passd.get("recipient") or {}
        out["pass"] = {
            "accurate": passd.get("accurate"),
            "recipient": {"id": recipient.get("id"), "name": recipient.get("name")} if recipient else None,
            "endLocation": passd.get("endLocation"),
            "length": passd.get("length"),
            "angle": passd.get("angle"),
        }

    shot = ev.get("shot")
    if shot:
        out["shot"] = {
            "onTarget": shot.get("onTarget"),
            "isGoal": shot.get("isGoal"),
            "xg": shot.get("xg"),
            "bodyPart": shot.get("bodyPart"),
        }

    gd = ev.get("groundDuel")
    if gd:
        opp = gd.get("opponent") or {}
        out["groundDuel"] = {
            "opponent": {"id": opp.get("id"), "name": opp.get("name")} if opp else None,
            "keptPossession": gd.get("keptPossession"),
            "recoveredPossession": gd.get("recoveredPossession"),
            "won": gd.get("won"),
        }

    ad = ev.get("aerialDuel")
    if ad:
        opp = ad.get("opponent") or {}
        out["aerialDuel"] = {
            "opponent": {"id": opp.get("id"), "name": opp.get("name")} if opp else None,
            "keptPossession": ad.get("keptPossession"),
            "recoveredPossession": ad.get("recoveredPossession"),
            "won": ad.get("won"),
        }

    carry = ev.get("carry")
    if carry:
        out["carry"] = {
            "endLocation": carry.get("endLocation"),
            "progression": carry.get("progression"),
        }

    infraction = ev.get("infraction")
    if infraction:
        out["infraction"] = {
            "type": infraction.get("type"),
            "yellowCard": infraction.get("yellowCard"),
            "redCard": infraction.get("redCard"),
        }

    poss = ev.get("possession")
    if poss:
        pteam = poss.get("team") or {}
        out["possession"] = {
            "id": poss.get("id"),
            "duration": poss.get("duration"),
            "types": poss.get("types") or [],
            "team": {"id": pteam.get("id"), "name": pteam.get("name")} if pteam else None,
            "endLocation": poss.get("endLocation"),
        }

    return out


def event_timecode_seconds(ev):
    """Convert an event's (matchPeriod, minute, second) to a total second offset
    from kick-off. 2nd half is offset by 45 minutes."""
    period_offset = 45 * 60 if ev.get("matchPeriod") == "2H" else 0
    m = ev.get("minute") or 0
    s = ev.get("second") or 0
    return period_offset + m * 60 + s


class SimState:
    """Thread-safe simulation clock."""

    def __init__(self, multiplier: float):
        self._lock = threading.Lock()
        self._t0 = time.monotonic()
        self._multiplier = float(multiplier)

    def reset(self):
        with self._lock:
            self._t0 = time.monotonic()

    def set_multiplier(self, m: float):
        with self._lock:
            # Reset T0 so the new speed doesn't skip/rewind the simulated clock.
            # We rebase T0 such that simulated seconds remain continuous.
            now = time.monotonic()
            elapsed_real = now - self._t0
            simulated_sec = elapsed_real * self._multiplier
            self._multiplier = float(m)
            if self._multiplier > 0:
                self._t0 = now - (simulated_sec / self._multiplier)

    def simulated_seconds(self) -> float:
        with self._lock:
            return (time.monotonic() - self._t0) * self._multiplier

    def snapshot(self):
        with self._lock:
            return {
                "t0": self._t0,
                "multiplier": self._multiplier,
                "simulatedSeconds": (time.monotonic() - self._t0) * self._multiplier,
            }


def make_handler(match_meta, events_sorted, state: SimState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "WyscoutMock/1.0"

        def log_message(self, fmt, *args):
            # Keep logs minimal — one line per request.
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} \"{self.requestline}\" {fmt % args}")

        def _json(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return {}

        def do_GET(self):
            if self.path.split("?", 1)[0] == "/events":
                self._serve_events()
            elif self.path == "/control/status":
                self._serve_status()
            else:
                self._json(404, {"error": "not_found", "path": self.path})

        def do_POST(self):
            if self.path == "/control/reset":
                state.reset()
                self._json(200, {"ok": True, "action": "reset", **state.snapshot()})
            elif self.path == "/control/speed":
                body = self._read_body()
                mult = body.get("multiplier")
                try:
                    mult_f = float(mult)
                except (TypeError, ValueError):
                    self._json(400, {"error": "invalid_multiplier", "received": mult})
                    return
                if mult_f <= 0:
                    self._json(400, {"error": "multiplier_must_be_positive"})
                    return
                state.set_multiplier(mult_f)
                self._json(200, {"ok": True, "action": "speed", **state.snapshot()})
            else:
                self._json(404, {"error": "not_found", "path": self.path})

        def _serve_events(self):
            sim_sec = state.simulated_seconds()
            # Binary-search-style cutoff. events_sorted is pre-sorted by timecode,
            # so a linear scan is fine for 755 events; simple and robust.
            cutoff = sim_sec
            filtered = [e for e in events_sorted if event_timecode_seconds(e) <= cutoff]

            if cutoff < 45 * 60:
                period = "1H"
                m = int(cutoff // 60)
                s = int(cutoff % 60)
            elif cutoff < 90 * 60:
                period = "2H"
                mins_into_2h = cutoff - 45 * 60
                m = 45 + int(mins_into_2h // 60)
                s = int(mins_into_2h % 60)
            else:
                period = "FT"
                m = 90
                s = 0

            status = "live"
            if cutoff >= 90 * 60:
                status = "finished"
            elif cutoff <= 0:
                status = "scheduled"

            payload = {
                "match": {
                    **match_meta,
                    "status": status,
                    "simulatedMinute": m,
                    "simulatedSecond": s,
                    "simulatedPeriod": period,
                },
                "events": filtered,
            }
            self._json(200, payload)

        def _serve_status(self):
            snap = state.snapshot()
            sim_sec = snap["simulatedSeconds"]
            delivered = sum(1 for e in events_sorted if event_timecode_seconds(e) <= sim_sec)
            self._json(200, {
                "simulatedSeconds": round(sim_sec, 2),
                "simulatedMinute": int(sim_sec // 60),
                "simulatedSecond": int(sim_sec % 60),
                "multiplier": snap["multiplier"],
                "eventsDrained": delivered,
                "eventsTotal": len(events_sorted),
                "startedAtMonotonic": snap["t0"],
                "serverTime": datetime.now(timezone.utc).isoformat(),
                "match": match_meta,
            })

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Wyscout mock live-match server")
    parser.add_argument("--input", "-i", type=Path,
                        default=Path("u_cluj_wyscout_mock_match_events_april_2026.json"),
                        help="Source Wyscout-style JSON")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", "-p", type=int, default=5001)
    parser.add_argument("--speed", "-s", type=float, default=10.0,
                        help="Simulation speed multiplier (10.0 = 10x real time)")
    args = parser.parse_args()

    print(f"Loading match from: {args.input}")
    match_meta, events = load_match(args.input)
    print(f"Match: {match_meta['label']} (wyId={match_meta['wyId']})")
    print(f"Loaded {len(events)} events. Speed multiplier: {args.speed}x")

    state = SimState(args.speed)
    handler = make_handler(match_meta, events, state)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving on http://{args.host}:{args.port}")
    print(f"  GET  /events            -> cumulative event feed")
    print(f"  GET  /control/status    -> sim clock + event count")
    print(f"  POST /control/reset     -> restart simulation at 0:00")
    print(f"  POST /control/speed     -> body {{\"multiplier\": N}}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
