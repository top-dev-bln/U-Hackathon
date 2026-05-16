"""Periodic recomputation thread."""

from __future__ import annotations

import logging
import threading
import time

from . import analyzer
from .config import Config
from .publisher import MatchStatsPublisher
from .store import MatchStore

log = logging.getLogger(__name__)


class RecomputeThread(threading.Thread):
    def __init__(self, store: MatchStore, publisher: MatchStatsPublisher,
                 stop_event: threading.Event):
        super().__init__(name="recompute", daemon=True)
        self._store = store
        self._publisher = publisher
        self._stop = stop_event
        self._interval = Config.RECOMPUTE_MS / 1000.0

    def run(self):
        log.info("Recompute loop tick = %.2fs", self._interval)
        while not self._stop.wait(self._interval):
            try:
                self._tick()
            except Exception as e:
                log.exception("Recompute tick failed: %s", e)

    def _tick(self):
        for match_id in self._store.match_ids():
            events = self._store.snapshot(match_id)
            if not events:
                continue
            home_id, away_id = self._store.teams(match_id)
            stats = analyzer.analyze_match(events, home_id, away_id, match_id=match_id)
            self._store.set_stats(match_id, stats)
            self._publisher.publish(match_id, stats)
            md = stats["metadata"]
            comp = stats.get("comparison") or {}
            tc = (comp.get("totalChains") or {})
            log.info(
                "match=%s events=%d chains=H%s/A%s",
                match_id,
                md["totalEvents"],
                tc.get(str(md["homeTeam"]["id"])) if md["homeTeam"]["id"] is not None else "?",
                tc.get(str(md["awayTeam"]["id"])) if md["awayTeam"]["id"] is not None else "?",
            )
