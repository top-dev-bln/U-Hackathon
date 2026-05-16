import json
import os
from pathlib import Path

DEFAULT_MOCK = (
    Path(__file__).resolve().parent
    / "mock_data"
    / "u_cluj_wyscout_mock_match_events_april_2026.json"
)


def load_match(source: str | Path | None = None) -> dict:
    path = Path(source) if source else Path(os.getenv("WYSCOUT_MOCK_PATH", DEFAULT_MOCK))
    with open(path) as f:
        data = json.load(f)
    return data["elements"][0]
