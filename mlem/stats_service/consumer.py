"""Kafka consumer thread that fills MatchStore from `wyscout-events`."""

from __future__ import annotations

import json
import logging
import threading

from confluent_kafka import Consumer, KafkaException

from .config import Config
from .store import MatchStore

log = logging.getLogger(__name__)


class KafkaConsumerThread(threading.Thread):
    def __init__(self, store: MatchStore, stop_event: threading.Event):
        super().__init__(name="kafka-consumer", daemon=True)
        self._store = store
        self._stop = stop_event
        self._consumer = Consumer({
            "bootstrap.servers": Config.KAFKA_BOOTSTRAP,
            "group.id": Config.GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        })

    def run(self):
        log.info("Subscribing to topic '%s' at %s", Config.IN_TOPIC, Config.KAFKA_BOOTSTRAP)
        self._consumer.subscribe([Config.IN_TOPIC])
        ingested = 0
        try:
            while not self._stop.is_set():
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    log.warning("Kafka error: %s", msg.error())
                    continue
                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                except (ValueError, UnicodeDecodeError) as e:
                    log.warning("Bad JSON on offset %s: %s", msg.offset(), e)
                    continue
                self._store.put(payload)
                ingested += 1
                if ingested % 100 == 0:
                    log.info("Ingested %d events (matches active: %s)",
                             ingested, self._store.match_ids())
        except KafkaException as e:
            log.exception("Consumer crashed: %s", e)
        finally:
            try:
                self._consumer.close()
            except Exception:
                pass
            log.info("Consumer thread stopped (ingested=%d)", ingested)
