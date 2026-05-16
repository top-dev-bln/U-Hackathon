from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer

from tactical_fusion.ingestion import ValidationError
from tactical_fusion.pipeline import run_fusion


class FusionHandler(BaseHTTPRequestHandler):
    def _json_response(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/fusion/analysis":
            self._json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
            input1 = payload["input1"]
            input2 = payload["input2"]
            result = run_fusion(input1, input2)
            self._json_response(result, HTTPStatus.OK)
        except (KeyError, json.JSONDecodeError):
            self._json_response(
                {"error": "Invalid JSON body. Expected: {\"input1\": {...}, \"input2\": {...}}"},
                HTTPStatus.BAD_REQUEST,
            )
        except ValidationError as exc:
            self._json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json_response({"status": "ok"}, HTTPStatus.OK)
            return
        self._json_response({"error": "Not Found"}, HTTPStatus.NOT_FOUND)


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = HTTPServer((host, port), FusionHandler)
    print(f"Tactical Fusion API listening on http://{host}:{port}")
    server.serve_forever()
