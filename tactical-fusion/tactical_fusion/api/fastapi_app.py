from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

from tactical_fusion.ingestion import ValidationError, load_json_file
from tactical_fusion.pipeline import run_fusion


class FusionJsonRequest(BaseModel):
    input1: dict[str, Any] = Field(..., description="Tactical Baseline payload")
    input2: dict[str, Any] = Field(..., description="Decision Quality payload")


def _load_default_calibration_config() -> dict[str, Any] | None:
    config_path = Path(__file__).resolve().parents[1] / "calibration_config.json"
    if not config_path.exists():
        return None
    return load_json_file(config_path)


def _read_upload_file(upload: UploadFile, field_name: str) -> dict[str, Any]:
    filename = upload.filename or ""
    if filename and not filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail=f"`{field_name}` must be a .json file")
    try:
        raw_content = upload.file.read()
        payload = json.loads(raw_content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail=f"`{field_name}` is not valid JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail=f"`{field_name}` must contain a JSON object")
    return payload


async def _extract_inputs(request: Request) -> tuple[dict[str, Any], dict[str, Any]]:
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object")
        input1 = payload.get("input1")
        input2 = payload.get("input2")
        if not isinstance(input1, dict) or not isinstance(input2, dict):
            raise HTTPException(
                status_code=400,
                detail='Expected JSON body: {"input1": {...}, "input2": {...}}',
            )
        return input1, input2

    if "multipart/form-data" in content_type:
        form = await request.form()
        input1_upload = form.get("input1") or form.get("input1_file")
        input2_upload = form.get("input2") or form.get("input2_file")

        if not isinstance(input1_upload, UploadFile) or not isinstance(input2_upload, UploadFile):
            raise HTTPException(
                status_code=400,
                detail="Multipart requires files for input1 and input2 (or input1_file/input2_file).",
            )
        input1 = _read_upload_file(input1_upload, "input1")
        input2 = _read_upload_file(input2_upload, "input2")
        return input1, input2

    raise HTTPException(
        status_code=415,
        detail="Unsupported Content-Type. Use application/json or multipart/form-data.",
    )


def _run_fusion_or_raise(
    input1: dict[str, Any],
    input2: dict[str, Any],
    calibration_config: dict[str, Any] | None,
) -> dict[str, Any]:
    try:
        return run_fusion(input1, input2, calibration_config=calibration_config)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def create_app() -> FastAPI:
    app = FastAPI(title="Tactical Fusion API", version="1.0.0")
    calibration_config = _load_default_calibration_config()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/fusion/analysis/json", summary="Fusion analysis from JSON body")
    async def fusion_analysis_json(payload: FusionJsonRequest) -> JSONResponse:
        result = _run_fusion_or_raise(payload.input1, payload.input2, calibration_config)
        return JSONResponse(content=result)

    @app.post("/fusion/analysis/multipart", summary="Fusion analysis from uploaded JSON files")
    async def fusion_analysis_multipart(
        input1: UploadFile = File(..., description="input1 JSON file"),
        input2: UploadFile = File(..., description="input2 JSON file"),
    ) -> JSONResponse:
        parsed_input1 = _read_upload_file(input1, "input1")
        parsed_input2 = _read_upload_file(input2, "input2")
        result = _run_fusion_or_raise(parsed_input1, parsed_input2, calibration_config)
        return JSONResponse(content=result)

    # Legacy compatibility endpoint (hidden from Swagger/OpenAPI docs).
    @app.post("/fusion/analysis", include_in_schema=False)
    async def fusion_analysis_legacy(request: Request) -> JSONResponse:
        input1, input2 = await _extract_inputs(request)
        result = _run_fusion_or_raise(input1, input2, calibration_config)
        return JSONResponse(content=result)

    return app


app = create_app()
