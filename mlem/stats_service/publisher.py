"""Kafka producer that republishes match-stats snapshots."""

from __future__ import annotations

import json
import logging

from confluent_kafka import Producer

from .config import Config

log = logging.getLogger(__name__)


class MatchStatsPublisher:
    def __init__(self):
        self._producer = Producer({
            "bootstrap.servers": Config.KAFKA_BOOTSTRAP,
            "linger.ms": 50,
        })

    def publish(self, match_id, stats: dict) -> None:
        try:
            self._producer.produce(
                Config.OUT_TOPIC,
                key=str(match_id).encode("utf-8"),
                value=json.dumps(stats, ensure_ascii=False).encode("utf-8"),
            )
            self._producer.poll(0)
        except BufferError:
            log.warning("Producer queue full; flushing")
            self._producer.flush(2.0)
        except Exception as e:
            log.exception("Failed to publish match-stats for %s: %s", match_id, e)

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)
