from __future__ import annotations

try:
    import uvicorn
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency `uvicorn`. Install: pip install fastapi uvicorn python-multipart"
    ) from exc

from tactical_fusion.api.fastapi_app import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
