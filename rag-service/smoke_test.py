from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parent


def load_json(name: str) -> dict:
    with (ROOT / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def build_payload() -> dict:
    tactical_baseline = load_json("input_tactical_intelligence.json")
    match_id = tactical_baseline["matchId"]
    team_id = tactical_baseline["teamId"]
    team_name = tactical_baseline["teamName"]
    return {
        "matchId": match_id,
        "teamId": team_id,
        "teamName": team_name,
        "source": "generated_models",
        "outputs": {
            "fusion": load_json("input_tactical_fusion.json"),
            "tacticalBaseline": tactical_baseline,
            "decisionQuality": load_json("input_decision_quality.json"),
            "playerProfiles": [load_json("input_player_profile.json")],
            "pressing": load_json("input_pressing.json"),
            "passingNetwork": load_json("input_passing_newtork.json"),
        },
        "options": {
            "vectorStore": "faiss",
            "rebuild": True,
            "topNPhases": 10,
            "includeDebugDocuments": False,
        },
    }


def run_smoke_test() -> None:
    payload = build_payload()
    match_id = payload["matchId"]

    with TestClient(app) as client:
        response = client.post("/index/match", json=payload)
        response.raise_for_status()
        data = response.json()

    assert data["status"] == "indexed"
    assert data["documentsCreated"] > 0
    assert data["embeddingsCreated"] == data["documentsCreated"]

    match_dir = ROOT / "storage" / "vector_store" / f"match_{match_id}"
    assert (match_dir / "index.faiss").exists()
    assert (match_dir / "documents.json").exists()

    print("Smoke test passed.")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    run_smoke_test()

