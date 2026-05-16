"""Entry point: starts the consumer + recompute threads, then serves FastAPI."""

from __future__ import annotations

import logging
import signal
import sys
import threading

import uvicorn

from .api import app, attach_store
from .config import Config
from .consumer import KafkaConsumerThread
from .publisher import MatchStatsPublisher
from .recompute import RecomputeThread
from .store import MatchStore


def main():
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("stats_service")
    log.info("Starting stats-service (kafka=%s in=%s out=%s)",
             Config.KAFKA_BOOTSTRAP, Config.IN_TOPIC, Config.OUT_TOPIC)

    store = MatchStore()
    attach_store(store)

    stop_event = threading.Event()

    publisher = MatchStatsPublisher()
    consumer = KafkaConsumerThread(store, stop_event)
    recompute = RecomputeThread(store, publisher, stop_event)

    consumer.start()
    recompute.start()

    def _on_signal(signum, frame):
        log.info("Signal %s received, shutting down", signum)
        stop_event.set()
        try:
            publisher.flush(2.0)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    uvicorn.run(app, host="0.0.0.0", port=Config.PORT, log_level=Config.LOG_LEVEL.lower())


if __name__ == "__main__":
    main()
