from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from smoke_test import build_payload

QUESTIONS = [
    "Care au fost principalele riscuri tactice?",
    "Ce jucatori trebuie prioritizati si de ce?",
    "Ce focus de antrenament recomanzi pentru build-up?",
]


def ensure_index(client: TestClient) -> int:
    payload = build_payload()
    response = client.post("/index/match", json=payload)
    response.raise_for_status()
    return int(payload["matchId"])


def run_smoke_rag() -> None:
    with TestClient(app) as client:
        match_id = ensure_index(client)
        session_id = "smoke-session-001"
        results = []

        for question in QUESTIONS:
            response = client.post(
                "/rag/query",
                json={
                    "sessionId": session_id,
                    "question": question,
                    "matchId": match_id,
                    "topK": 6,
                },
            )
            response.raise_for_status()
            payload = response.json()
            assert payload["sessionId"] == session_id
            assert payload["answer"].strip()
            assert payload["retrievedCount"] > 0
            assert payload["sources"]
            results.append(payload)

        debug_response = client.post(
            "/rag/query/debug",
            json={
                "sessionId": session_id,
                "question": QUESTIONS[0],
                "matchId": match_id,
                "topK": 6,
            },
        )
        debug_response.raise_for_status()
        debug_payload = debug_response.json()
        assert debug_payload["sessionId"] == session_id
        assert debug_payload["context"].strip()
        assert debug_payload["retrievedDocuments"]

        history_resp = client.get(f"/rag/sessions/{session_id}/history")
        history_resp.raise_for_status()
        history = history_resp.json()
        assert len(history) <= 5
        assert history

        reset_resp = client.post(f"/rag/sessions/{session_id}/reset")
        reset_resp.raise_for_status()
        reset_payload = reset_resp.json()
        assert reset_payload["sessionId"] == session_id
        assert reset_payload["cleared"] is True

    print("RAG smoke test passed.")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps({"debugModel": debug_payload["model"], "debugRetrieved": debug_payload["retrievedCount"]}, indent=2))


if __name__ == "__main__":
    run_smoke_rag()
