from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from .api_service import MatchRequestPayload, TacticalInsightsService

app = FastAPI(
    title="Tactical Insights API",
    version="1.0.0",
    description="API for league baseline and tactical insights generated from players_stats inputs.",
)
service = TacticalInsightsService()


class MatchInsightsRequest(BaseModel):
    players_stats: dict[str, Any] = Field(..., description="Raw players_stats JSON payload for one match.")
    home_team_name: str = Field(..., description="Home team name for the submitted match.")
    away_team_name: str = Field(..., description="Away team name for the submitted match.")
    match_id: int | None = Field(
        default=None,
        description="Optional override for matchId. If omitted, it is inferred from payload or generated.",
    )
    home_score: int | None = Field(default=None, description="Optional home score.")
    away_score: int | None = Field(default=None, description="Optional away score.")
    focus_team_name: str | None = Field(
        default=None,
        description="Optional team name filter. If provided, response keeps only this team in finalReport.",
    )


def _build_live_report_or_http_error(payload: MatchRequestPayload) -> dict[str, Any]:
    try:
        return service.build_live_match_report(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - API safety net
        raise HTTPException(status_code=500, detail=f"Failed to build insights: {exc}") from exc


def _build_compact_report_or_http_error(
    payload: MatchRequestPayload,
    *,
    top_insights: int,
    top_strengths: int,
) -> dict[str, Any]:
    try:
        return service.build_live_match_report_compact(
            payload,
            top_insights=top_insights,
            top_strengths=top_strengths,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - API safety net
        raise HTTPException(status_code=500, detail=f"Failed to build compact insights: {exc}") from exc


def _build_detailed_report_or_http_error(payload: MatchRequestPayload) -> dict[str, Any]:
    try:
        return service.build_live_match_report_detailed(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - API safety net
        raise HTTPException(status_code=500, detail=f"Failed to build detailed insights: {exc}") from exc


async def _payload_from_multipart(
    *,
    players_stats_file: UploadFile,
    home_team_name: str,
    away_team_name: str,
    match_id: int | None,
    home_score: int | None,
    away_score: int | None,
    focus_team_name: str | None,
) -> MatchRequestPayload:
    if players_stats_file.filename and not players_stats_file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Uploaded file must have .json extension.")

    try:
        raw = (await players_stats_file.read()).decode("utf-8")
        players_stats = json.loads(raw)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Uploaded file is not valid UTF-8 JSON: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in uploaded file: {exc}") from exc

    if not isinstance(players_stats, dict):
        raise HTTPException(status_code=400, detail="Uploaded JSON must be an object with 'players' field.")

    return MatchRequestPayload(
        players_stats=players_stats,
        home_team_name=home_team_name,
        away_team_name=away_team_name,
        match_id=match_id,
        home_score=home_score,
        away_score=away_score,
        focus_team_name=focus_team_name,
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    return service.get_health()


@app.get("/api/league/baseline")
def league_baseline() -> dict[str, Any]:
    baseline = service.get_league_baseline()
    if not baseline:
        raise HTTPException(status_code=404, detail="league_baseline.json not found.")
    return baseline


@app.get("/api/league/distributions")
def league_distributions() -> dict[str, Any]:
    distributions = service.get_league_distributions()
    if not distributions:
        raise HTTPException(status_code=404, detail="league_distributions.json not found.")
    return distributions


@app.get("/api/matches/{match_id}/tactical-weaknesses")
def precomputed_match_report(match_id: int) -> dict[str, Any]:
    report = service.get_precomputed_match_report(match_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found in precomputed report.")
    return report


@app.get("/api/matches/{match_id}/tactical-profile")
def precomputed_match_tactical_profile(match_id: int) -> dict[str, Any]:
    rows = service.get_precomputed_tactical_profile(match_id)
    if not rows:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found in tactical clusters.")
    return {"matchId": match_id, "rows": rows}


@app.post("/api/insights/from-players-stats")
def insights_from_players_stats(request: MatchInsightsRequest) -> dict[str, Any]:
    payload = MatchRequestPayload(
        players_stats=request.players_stats,
        home_team_name=request.home_team_name,
        away_team_name=request.away_team_name,
        match_id=request.match_id,
        home_score=request.home_score,
        away_score=request.away_score,
        focus_team_name=request.focus_team_name,
    )
    return _build_live_report_or_http_error(payload)


@app.post("/api/insights/compact/from-players-stats")
def compact_insights_from_players_stats(
    request: MatchInsightsRequest,
    top_insights: int = Query(default=2, ge=1, le=10),
    top_strengths: int = Query(default=2, ge=1, le=10),
) -> dict[str, Any]:
    payload = MatchRequestPayload(
        players_stats=request.players_stats,
        home_team_name=request.home_team_name,
        away_team_name=request.away_team_name,
        match_id=request.match_id,
        home_score=request.home_score,
        away_score=request.away_score,
        focus_team_name=request.focus_team_name,
    )
    return _build_compact_report_or_http_error(payload, top_insights=top_insights, top_strengths=top_strengths)


@app.post("/api/insights/detailed/from-players-stats")
def detailed_insights_from_players_stats(request: MatchInsightsRequest) -> dict[str, Any]:
    payload = MatchRequestPayload(
        players_stats=request.players_stats,
        home_team_name=request.home_team_name,
        away_team_name=request.away_team_name,
        match_id=request.match_id,
        home_score=request.home_score,
        away_score=request.away_score,
        focus_team_name=request.focus_team_name,
    )
    return _build_detailed_report_or_http_error(payload)


@app.post("/api/insights/from-players-stats-multipart")
async def insights_from_players_stats_multipart(
    players_stats_file: UploadFile = File(..., description="Upload a Wyscout *_players_stats.json file."),
    home_team_name: str = Form(..., description="Home team name for the uploaded match."),
    away_team_name: str = Form(..., description="Away team name for the uploaded match."),
    match_id: int | None = Form(default=None, description="Optional override for matchId."),
    home_score: int | None = Form(default=None, description="Optional home score."),
    away_score: int | None = Form(default=None, description="Optional away score."),
    focus_team_name: str | None = Form(default=None, description="Optional team name filter."),
) -> dict[str, Any]:
    payload = await _payload_from_multipart(
        players_stats_file=players_stats_file,
        home_team_name=home_team_name,
        away_team_name=away_team_name,
        match_id=match_id,
        home_score=home_score,
        away_score=away_score,
        focus_team_name=focus_team_name,
    )
    return _build_live_report_or_http_error(payload)


@app.post("/api/insights/compact/from-players-stats-multipart")
async def compact_insights_from_players_stats_multipart(
    players_stats_file: UploadFile = File(..., description="Upload a Wyscout *_players_stats.json file."),
    home_team_name: str = Form(..., description="Home team name for the uploaded match."),
    away_team_name: str = Form(..., description="Away team name for the uploaded match."),
    match_id: int | None = Form(default=None, description="Optional override for matchId."),
    home_score: int | None = Form(default=None, description="Optional home score."),
    away_score: int | None = Form(default=None, description="Optional away score."),
    focus_team_name: str | None = Form(default=None, description="Optional team name filter."),
    top_insights: int = Query(default=2, ge=1, le=10),
    top_strengths: int = Query(default=2, ge=1, le=10),
) -> dict[str, Any]:
    payload = await _payload_from_multipart(
        players_stats_file=players_stats_file,
        home_team_name=home_team_name,
        away_team_name=away_team_name,
        match_id=match_id,
        home_score=home_score,
        away_score=away_score,
        focus_team_name=focus_team_name,
    )
    return _build_compact_report_or_http_error(payload, top_insights=top_insights, top_strengths=top_strengths)


@app.post("/api/insights/detailed/from-players-stats-multipart")
async def detailed_insights_from_players_stats_multipart(
    players_stats_file: UploadFile = File(..., description="Upload a Wyscout *_players_stats.json file."),
    home_team_name: str = Form(..., description="Home team name for the uploaded match."),
    away_team_name: str = Form(..., description="Away team name for the uploaded match."),
    match_id: int | None = Form(default=None, description="Optional override for matchId."),
    home_score: int | None = Form(default=None, description="Optional home score."),
    away_score: int | None = Form(default=None, description="Optional away score."),
    focus_team_name: str | None = Form(default=None, description="Optional team name filter."),
) -> dict[str, Any]:
    payload = await _payload_from_multipart(
        players_stats_file=players_stats_file,
        home_team_name=home_team_name,
        away_team_name=away_team_name,
        match_id=match_id,
        home_score=home_score,
        away_score=away_score,
        focus_team_name=focus_team_name,
    )
    return _build_detailed_report_or_http_error(payload)
