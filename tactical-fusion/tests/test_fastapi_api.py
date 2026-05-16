from __future__ import annotations

import importlib.util
import io
import json
import unittest
from pathlib import Path

from tactical_fusion.ingestion import load_json_file

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None
HTTPX_AVAILABLE = importlib.util.find_spec("httpx") is not None
if FASTAPI_AVAILABLE:
    TESTCLIENT_AVAILABLE = importlib.util.find_spec("fastapi.testclient") is not None
else:
    TESTCLIENT_AVAILABLE = False


@unittest.skipUnless(
    FASTAPI_AVAILABLE and TESTCLIENT_AVAILABLE and HTTPX_AVAILABLE,
    "FastAPI test dependencies not installed",
)
class FastApiFusionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from fastapi.testclient import TestClient

        from tactical_fusion.api.fastapi_app import create_app

        root = Path(__file__).resolve().parent.parent
        cls.input1 = load_json_file(root / "input1.json")
        cls.input2 = load_json_file(root / "input2.json")
        cls.client = TestClient(create_app())

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_fusion_analysis_json_body(self) -> None:
        response = self.client.post(
            "/fusion/analysis/json",
            json={"input1": self.input1, "input2": self.input2},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("fusionOutput", body)
        self.assertIn("frontendOutput", body)

    def test_fusion_analysis_multipart_files(self) -> None:
        input1_content = json.dumps(self.input1).encode("utf-8")
        input2_content = json.dumps(self.input2).encode("utf-8")
        files = {
            "input1": ("input1.json", io.BytesIO(input1_content), "application/json"),
            "input2": ("input2.json", io.BytesIO(input2_content), "application/json"),
        }
        response = self.client.post("/fusion/analysis/multipart", files=files)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("fusionOutput", body)
        self.assertIn("frontendOutput", body)


if __name__ == "__main__":
    unittest.main()
