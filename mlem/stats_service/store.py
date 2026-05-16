"""Thread-safe per-match event buffer + analysis cache."""

from __future__ import annotations

import threading
import time
from typing import Optional


def _event_timecode(ev) -> tuple:
    period_rank = 0 if ev.get("matchPeriod") == "1H" else 1
    return (period_rank, ev.get("minute") or 0, ev.get("second") or 0, ev.get("id") or 0)


class MatchStore:
    def __init__(self):
        self._lock = threading.RLock()
        # matchId -> {events: dict[id, ev], teams_seen: list[int], stats: dict|None, last_update: float}
        self._matches: dict = {}

    def put(self, event: dict) -> None:
        match_id = event.get("matchId")
        eid = event.get("id")
        if match_id is None or eid is None:
            return
        with self._lock:
            entry = self._matches.get(match_id)
            if entry is None:
                entry = {
                    "events": {},
                    "teams_seen": [],
                    "stats": None,
                    "last_update": time.time(),
                }
                self._matches[match_id] = entry
            entry["events"][eid] = event
            entry["last_update"] = time.time()

            team = event.get("team") or {}
            tid = team.get("id")
            if tid is not None and tid not in entry["teams_seen"]:
                entry["teams_seen"].append(tid)

    def snapshot(self, match_id) -> list:
        with self._lock:
            entry = self._matches.get(match_id)
            if entry is None:
                return []
            evs = list(entry["events"].values())
        evs.sort(key=_event_timecode)
        return evs

    def teams(self, match_id) -> tuple:
        with self._lock:
            entry = self._matches.get(match_id)
            if entry is None:
                return (None, None)
            seen = list(entry["teams_seen"])
        if len(seen) >= 2:
            return (seen[0], seen[1])
        if len(seen) == 1:
            return (seen[0], None)
        return (None, None)

    def match_ids(self) -> list:
        with self._lock:
            return list(self._matches.keys())

    def summary(self) -> list:
        with self._lock:
            return [
                {
                    "matchId": mid,
                    "eventCount": len(entry["events"]),
                    "teamsSeen": list(entry["teams_seen"]),
                    "lastUpdate": entry["last_update"],
                }
                for mid, entry in self._matches.items()
            ]

    def latest_stats(self, match_id) -> Optional[dict]:
        with self._lock:
            entry = self._matches.get(match_id)
            return entry["stats"] if entry else None

    def set_stats(self, match_id, stats: dict) -> None:
        with self._lock:
            entry = self._matches.get(match_id)
            if entry is None:
                return
            entry["stats"] = stats
