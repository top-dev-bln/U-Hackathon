from __future__ import annotations

import json
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tactical_fusion.api.server import FusionHandler
from tactical_fusion.ingestion import load_json_file


class FusionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parent.parent
        cls.input1 = load_json_file(root / "input1.json")
        cls.input2 = load_json_file(root / "input2.json")

        cls.server = HTTPServer(("127.0.0.1", 0), FusionHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_health_endpoint(self) -> None:
        with urlopen(self._url("/health"), timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
        self.assertEqual(body["status"], "ok")

    def test_fusion_analysis_endpoint(self) -> None:
        request_body = json.dumps({"input1": self.input1, "input2": self.input2}).encode("utf-8")
        request = Request(
            self._url("/fusion/analysis"),
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
        self.assertIn("fusionOutput", body)
        self.assertIn("frontendOutput", body)

    def test_invalid_request_returns_bad_request(self) -> None:
        request = Request(
            self._url("/fusion/analysis"),
            data=b'{"input1": {}}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as exc:
            urlopen(request, timeout=2)
        self.assertEqual(exc.exception.code, 400)
        exc.exception.close()


if __name__ == "__main__":
    unittest.main()
