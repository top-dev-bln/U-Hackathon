"""Service config from environment variables."""

import os


class Config:
    KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
    IN_TOPIC = os.environ.get("IN_TOPIC", "wyscout-events")
    OUT_TOPIC = os.environ.get("OUT_TOPIC", "match-stats")
    GROUP_ID = os.environ.get("GROUP_ID", "stats-service")
    RECOMPUTE_MS = int(os.environ.get("RECOMPUTE_MS", "2000"))
    PORT = int(os.environ.get("PORT", "8000"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
