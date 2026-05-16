from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, ValidationError, model_validator

from decision_quality_pipeline import (
    ACTION_TYPES,
    add_context_features,
    build_feature_matrix,
    create_label,
    summarize_events,
    summarize_players,
)


DEFAULT_MODEL_PATH = Path("u_cluj_decision_quality_model.joblib")
DEFAULT_SAMPLE_JSON_PATH = Path("u_cluj_10_matches_wyscout_events_combined.json")


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = np.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    return lowered in {"1", "true", "yes"}


def _safe_round_records(df: pd.DataFrame, round_cols: List[str], ndigits: int = 4) -> List[Dict[str, Any]]:
    out = df.copy()
    for col in round_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(ndigits)
    out = out.astype(object).where(pd.notna(out), None)
    return out.to_dict(orient="records")


def _element_match_id(element: Dict[str, Any]) -> Optional[str]:
    match = element.get("match", {}) or {}
    match_id = match.get("wyId") or match.get("id")
    if match_id is not None:
        return str(match_id)

    events = element.get("events", []) or []
    if events:
        ev_match_id = events[0].get("matchId")
        if ev_match_id is not None:
            return str(ev_match_id)
    return None


def extract_match_elements(payload: Any) -> List[Dict[str, Any]]:
    elements: List[Dict[str, Any]] = []

    if isinstance(payload, dict):
        if "matches" in payload and isinstance(payload["matches"], list):
            for item in payload["matches"]:
                if not isinstance(item, dict):
                    continue
                raw_elements = item.get("elements", [])
                if isinstance(raw_elements, list):
                    for el in raw_elements:
                        if isinstance(el, dict):
                            elements.append(el)
            return elements

        if "elements" in payload and isinstance(payload["elements"], list):
            for el in payload["elements"]:
                if isinstance(el, dict):
                    elements.append(el)
            return elements

        if "match" in payload and "events" in payload:
            return [payload]

        if "events" in payload and isinstance(payload["events"], list):
            return [
                {
                    "match": payload.get("match", {}),
                    "teams": payload.get("teams", {}),
                    "players": payload.get("players", {}),
                    "events": payload.get("events", []),
                }
            ]

    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "type" in payload[0]:
            return [{"match": {}, "teams": {}, "players": {}, "events": payload}]
        for item in payload:
            if isinstance(item, dict) and "events" in item:
                elements.append(item)
        return elements

    return []


def select_match_element(payload: Any, requested_match_id: Optional[int]) -> Dict[str, Any]:
    elements = extract_match_elements(payload)
    if not elements:
        raise ValueError("Payload does not contain a valid match/events structure.")

    if requested_match_id is not None:
        requested = str(requested_match_id)
        matched = [el for el in elements if _element_match_id(el) == requested]
        if not matched:
            available = sorted({m for m in (_element_match_id(el) for el in elements) if m is not None})
            raise ValueError(f"match_id={requested_match_id} not found. Available match ids: {available}")
        if len(matched) > 1:
            return matched[0]
        return matched[0]

    if len(elements) == 1:
        return elements[0]

    available = sorted({m for m in (_element_match_id(el) for el in elements) if m is not None})
    raise ValueError(
        "Payload contains multiple matches. Provide match_id in request. "
        f"Available match ids: {available}"
    )


def flatten_match_element(element: Dict[str, Any]) -> pd.DataFrame:
    teams = element.get("teams", {}) or {}
    players = element.get("players", {}) or {}
    events = element.get("events", []) or []

    if not isinstance(events, list) or len(events) == 0:
        return pd.DataFrame()

    team_name_lookup = {
        str(k): (v.get("name") if isinstance(v, dict) else None)
        for k, v in teams.items()
    }
    player_lookup = {
        str(k): (v if isinstance(v, dict) else {})
        for k, v in players.items()
    }

    default_match_id = _to_int((_element_match_id(element) or 0), default=0)
    rows: List[Dict[str, Any]] = []

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        event_type = event.get("type", {}) or {}
        event_primary = event_type.get("primary")
        if event_primary not in ACTION_TYPES:
            continue

        team = event.get("team", {}) or {}
        player = event.get("player", {}) or {}
        location = event.get("location", {}) or {}
        pass_data = event.get("pass", {}) or {}
        shot_data = event.get("shot", {}) or {}
        carry_data = event.get("carry", {}) or {}
        possession = event.get("possession", {}) or {}
        possession_attack = possession.get("attack", {}) or {}
        pass_recipient = pass_data.get("recipient", {}) or {}
        pass_end = pass_data.get("endLocation", {}) or {}
        carry_end = carry_data.get("endLocation", {}) or {}

        team_id = team.get("id")
        player_id = player.get("id")
        player_meta = player_lookup.get(str(player_id), {})

        team_name = team.get("name") or team_name_lookup.get(str(team_id)) or "Unknown Team"
        player_name = player.get("name") or player_meta.get("name") or "Unknown Player"
        position = player.get("position") or player_meta.get("position") or "UNK"

        rows.append(
            {
                "event_id": _to_int(event.get("id"), default=idx + 1),
                "match_id": _to_int(event.get("matchId"), default=default_match_id),
                "period": event.get("matchPeriod") or "UNK",
                "minute": _to_int(event.get("minute"), default=0),
                "second": _to_int(event.get("second"), default=0),
                "team_id": str(team_id) if team_id is not None else "",
                "team_name": team_name,
                "player_id": str(player_id) if player_id is not None else "",
                "player_name": player_name,
                "position": position,
                "event_primary": event_primary,
                "x": _to_float(location.get("x"), default=np.nan),
                "y": _to_float(location.get("y"), default=np.nan),
                "pass_accurate": pass_data.get("accurate"),
                "pass_recipient_id": pass_recipient.get("id"),
                "pass_recipient_name": pass_recipient.get("name"),
                "pass_end_x": _to_float(pass_end.get("x"), default=np.nan),
                "pass_end_y": _to_float(pass_end.get("y"), default=np.nan),
                "pass_length": _to_float(pass_data.get("length"), default=np.nan),
                "pass_angle": _to_float(pass_data.get("angle"), default=np.nan),
                "shot_xg": _to_float(shot_data.get("xg"), default=np.nan),
                "shot_on_target": shot_data.get("onTarget"),
                "shot_is_goal": shot_data.get("isGoal"),
                "carry_end_x": _to_float(carry_end.get("x"), default=np.nan),
                "carry_end_y": _to_float(carry_end.get("y"), default=np.nan),
                "possession_id": possession.get("id"),
                "possession_flank": possession_attack.get("flank"),
                "possession_with_shot": possession_attack.get("withShot"),
                "possession_with_goal": possession_attack.get("withGoal"),
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values(by=["match_id", "minute", "second", "event_id"], kind="mergesort").reset_index(drop=True)
    df["absolute_second"] = pd.to_numeric(df["minute"], errors="coerce").fillna(0).astype(int) * 60 + pd.to_numeric(
        df["second"], errors="coerce"
    ).fillna(0).astype(int)
    return df


def match_metadata(element: Dict[str, Any]) -> Dict[str, Any]:
    match = element.get("match", {}) or {}
    teams_raw = element.get("teams", {}) or {}

    teams = []
    if isinstance(teams_raw, dict):
        for t in teams_raw.values():
            if isinstance(t, dict):
                teams.append(
                    {
                        "teamId": t.get("id"),
                        "teamName": t.get("name"),
                        "formation": t.get("formation"),
                    }
                )

    return {
        "matchId": match.get("wyId") or match.get("id"),
        "label": match.get("label"),
        "date": match.get("date"),
        "status": match.get("status"),
        "venue": match.get("venue"),
        "teams": teams,
    }


@lru_cache(maxsize=4)
def load_model_cached(model_path: str):
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    return joblib.load(path)


@lru_cache(maxsize=2)
def load_json_payload_cached(json_path: str) -> Any:
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Sample JSON file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON content in sample file {path}: {e.msg}") from e


class AnalyzeMatchRequest(BaseModel):
    match_data: Dict[str, Any] = Field(..., description="Wyscout-style JSON with one match or multiple matches.")
    match_id: Optional[int] = Field(default=None, description="Required only if payload includes multiple matches.")
    team_name: Optional[str] = Field(default=None, description="Optional team filter for output.")
    low_score_quantile: float = Field(default=0.25, gt=0.0, lt=1.0)
    min_improvement: float = Field(default=0.02, ge=0.0)
    min_player_actions: int = Field(default=8, ge=1)
    top_n: int = Field(default=10, ge=1, le=50)
    window_seconds: int = Field(default=10, ge=1, le=30)
    model_path: str = Field(default=str(DEFAULT_MODEL_PATH))


class PhaseDecisionRequest(AnalyzeMatchRequest):
    event_id: Optional[int] = Field(default=None)
    minute: Optional[int] = Field(default=None, ge=0)
    second: Optional[int] = Field(default=None, ge=0)
    player_name: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_selector(self):
        if self.event_id is None and self.minute is None:
            raise ValueError("Provide event_id or at least minute/second (+ optional player_name).")
        return self


class AnalyzeMatchDemoRequest(BaseModel):
    sample_json_path: str = Field(default=str(DEFAULT_SAMPLE_JSON_PATH))
    match_id: Optional[int] = Field(default=99042601)
    team_name: Optional[str] = Field(default="FC Universitatea Cluj")
    low_score_quantile: float = Field(default=0.25, gt=0.0, lt=1.0)
    min_improvement: float = Field(default=0.02, ge=0.0)
    min_player_actions: int = Field(default=8, ge=1)
    top_n: int = Field(default=10, ge=1, le=50)
    window_seconds: int = Field(default=10, ge=1, le=30)
    model_path: str = Field(default=str(DEFAULT_MODEL_PATH))


class PhaseDecisionDemoRequest(AnalyzeMatchDemoRequest):
    event_id: Optional[int] = Field(default=880100003)
    minute: Optional[int] = Field(default=None, ge=0)
    second: Optional[int] = Field(default=None, ge=0)
    player_name: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_selector(self):
        if self.event_id is None and self.minute is None:
            raise ValueError("Provide event_id or at least minute/second (+ optional player_name).")
        return self


def _missed_opportunities_df(events: pd.DataFrame, min_improvement: float) -> pd.DataFrame:
    if len(events) == 0:
        return events.iloc[0:0].copy()
    high_value_cut = float(events["bestDecisionValue"].quantile(0.85))
    return events[
        (events["bestDecisionValue"] >= high_value_cut)
        & (events["potentialGain"] >= min_improvement)
        & (~events["actualGoal"])
        & (~events["actualShotOnTarget"])
    ].copy()


def _phase_records(events: pd.DataFrame, top_n: int, min_improvement: float) -> Dict[str, List[Dict[str, Any]]]:
    phase_cols = [
        "event_id",
        "minute",
        "second",
        "player_name",
        "team_name",
        "decision",
        "decisionValue",
        "bestDecisionType",
        "bestDecisionValue",
        "potentialGain",
        "suggestedAlternative",
        "label",
        "actualShotOnTarget",
        "actualGoal",
    ]

    best = events.sort_values("decisionValue", ascending=False).head(top_n)[phase_cols]
    improvable = (
        events[events["suggestedAlternative"].notna()]
        .sort_values("potentialGain", ascending=False)
        .head(top_n)[phase_cols]
    )

    missed_all = _missed_opportunities_df(events, min_improvement=min_improvement)
    missed = (
        missed_all
        .sort_values(["bestDecisionValue", "potentialGain"], ascending=[False, False])
        .head(top_n)[phase_cols]
    )

    round_cols = ["decisionValue", "bestDecisionValue", "potentialGain"]
    return {
        "bestPhases": _safe_round_records(best, round_cols),
        "improvablePhases": _safe_round_records(improvable, round_cols),
        "missedShotOrGoalOpportunities": _safe_round_records(missed, round_cols),
    }


def _player_sections(players: pd.DataFrame, top_n: int) -> Dict[str, List[Dict[str, Any]]]:
    cols = [
        "player_id",
        "player_name",
        "decisionScore",
        "actionsAnalyzed",
        "lowScoreActions",
        "suggestedActions",
        "avgPotentialGainOnSuggestions",
        "recommendedDecisionTypeWhenLow",
        "bestDecisionType",
        "weakDecisionType",
        "needsDecisionSupport",
    ]
    round_cols = ["decisionScore", "avgPotentialGainOnSuggestions"]
    top_performers = players.sort_values("decisionScore", ascending=False).head(top_n)[cols]
    underperformers = players.sort_values("decisionScore", ascending=True).head(top_n)[cols]
    needs_support = (
        players[players["needsDecisionSupport"]]
        .sort_values("decisionScore", ascending=True)
        .head(top_n)[cols]
    )

    return {
        "topPerformers": _safe_round_records(top_performers, round_cols),
        "underperformers": _safe_round_records(underperformers, round_cols),
        "needsSupport": _safe_round_records(needs_support, round_cols),
    }


def _timeline_stats(events: pd.DataFrame) -> List[Dict[str, Any]]:
    if len(events) == 0:
        return []

    timeline = events.copy()
    timeline["bucket_start"] = (pd.to_numeric(timeline["minute"], errors="coerce").fillna(0).astype(int) // 15) * 15
    agg = (
        timeline.groupby("bucket_start", as_index=False)
        .agg(
            actions=("event_id", "count"),
            avgDecisionValue=("decisionValue", "mean"),
            lowDecisionPhases=("isLowDecision", "sum"),
            phasesWithAlternative=("suggestedAlternative", lambda s: int(s.notna().sum())),
        )
        .sort_values("bucket_start")
        .reset_index(drop=True)
    )
    agg["minuteBucket"] = agg["bucket_start"].astype(int).astype(str) + "-" + (agg["bucket_start"] + 14).astype(int).astype(str)
    agg = agg.drop(columns=["bucket_start"])
    return _safe_round_records(agg, ["avgDecisionValue"])


def _decision_type_stats(events: pd.DataFrame) -> List[Dict[str, Any]]:
    if len(events) == 0:
        return []
    agg = (
        events.groupby("decision", as_index=False)
        .agg(
            actions=("event_id", "count"),
            avgDecisionValue=("decisionValue", "mean"),
            avgPotentialGain=("potentialGain", "mean"),
            lowDecisionPhases=("isLowDecision", "sum"),
        )
        .sort_values("avgDecisionValue", ascending=False)
    )
    return _safe_round_records(agg, ["avgDecisionValue", "avgPotentialGain"])


def analyze_match(
    request: AnalyzeMatchRequest,
) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    try:
        element = select_match_element(request.match_data, request.match_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    flat = flatten_match_element(element)
    if len(flat) == 0:
        raise HTTPException(
            status_code=400,
            detail="No offensive actions found in payload (supported: pass, shot, carry).",
        )
    flat["shot_is_goal_bool"] = flat.get("shot_is_goal", pd.Series([False] * len(flat))).apply(_to_bool)

    enriched = add_context_features(flat)
    enriched["label"] = create_label(enriched, window_seconds=request.window_seconds)

    X, _, _ = build_feature_matrix(enriched)
    try:
        model = load_model_cached(request.model_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    events, low_threshold = summarize_events(
        base_df=enriched,
        feature_df=X,
        model=model,
        low_score_quantile=request.low_score_quantile,
        min_improvement=request.min_improvement,
    )
    events["actualShotOnTarget"] = enriched.get("shot_on_target", pd.Series([False] * len(events))).apply(_to_bool).to_numpy()
    events["actualGoal"] = enriched.get("shot_is_goal", pd.Series([False] * len(events))).apply(_to_bool).to_numpy()

    players = summarize_players(events, min_player_actions=request.min_player_actions)

    if request.team_name:
        team_name = request.team_name.strip().lower()
        events = events[events["team_name"].astype(str).str.lower() == team_name].copy()
        player_ids = set(events["player_id"].astype(str).unique())
        players = players[players["player_id"].astype(str).isin(player_ids)].copy()

    missed_opportunities = _missed_opportunities_df(events, min_improvement=request.min_improvement)

    summary = {
        "actionsAnalyzed": int(len(events)),
        "playersAnalyzed": int(len(players)),
        "averageDecisionValue": float(events["decisionValue"].mean()) if len(events) else 0.0,
        "lowDecisionPhases": int(events["isLowDecision"].sum()) if len(events) else 0,
        "phasesWithAlternative": int(events["suggestedAlternative"].notna().sum()) if len(events) else 0,
        "missedShotOrGoalOpportunities": int(len(missed_opportunities)),
        "lowScoreThresholdUsed": float(low_threshold),
    }

    metadata = match_metadata(element)
    metadata["teamScope"] = request.team_name or "all_teams"

    return {"match": metadata, "summary": summary}, events, players


async def _parse_uploaded_json_file(file: UploadFile) -> Any:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file is missing filename.")
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are supported.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="JSON file must be UTF-8 encoded.") from e

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e.msg}") from e
    return payload


def _build_analyze_request(
    payload: Any,
    match_id: Optional[int],
    team_name: Optional[str],
    low_score_quantile: float,
    min_improvement: float,
    min_player_actions: int,
    top_n: int,
    window_seconds: int,
    model_path: str,
) -> AnalyzeMatchRequest:
    try:
        return AnalyzeMatchRequest(
            match_data=payload,
            match_id=match_id,
            team_name=team_name,
            low_score_quantile=low_score_quantile,
            min_improvement=min_improvement,
            min_player_actions=min_player_actions,
            top_n=top_n,
            window_seconds=window_seconds,
            model_path=model_path,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e


def _build_phase_request(
    payload: Any,
    match_id: Optional[int],
    team_name: Optional[str],
    low_score_quantile: float,
    min_improvement: float,
    min_player_actions: int,
    top_n: int,
    window_seconds: int,
    model_path: str,
    event_id: Optional[int],
    minute: Optional[int],
    second: Optional[int],
    player_name: Optional[str],
) -> PhaseDecisionRequest:
    try:
        return PhaseDecisionRequest(
            match_data=payload,
            match_id=match_id,
            team_name=team_name,
            low_score_quantile=low_score_quantile,
            min_improvement=min_improvement,
            min_player_actions=min_player_actions,
            top_n=top_n,
            window_seconds=window_seconds,
            model_path=model_path,
            event_id=event_id,
            minute=minute,
            second=second,
            player_name=player_name,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e


def _build_analyze_request_from_demo(request: AnalyzeMatchDemoRequest) -> AnalyzeMatchRequest:
    try:
        payload = load_json_payload_cached(request.sample_json_path)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _build_analyze_request(
        payload=payload,
        match_id=request.match_id,
        team_name=request.team_name,
        low_score_quantile=request.low_score_quantile,
        min_improvement=request.min_improvement,
        min_player_actions=request.min_player_actions,
        top_n=request.top_n,
        window_seconds=request.window_seconds,
        model_path=request.model_path,
    )


def _build_phase_request_from_demo(request: PhaseDecisionDemoRequest) -> PhaseDecisionRequest:
    try:
        payload = load_json_payload_cached(request.sample_json_path)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _build_phase_request(
        payload=payload,
        match_id=request.match_id,
        team_name=request.team_name,
        low_score_quantile=request.low_score_quantile,
        min_improvement=request.min_improvement,
        min_player_actions=request.min_player_actions,
        top_n=request.top_n,
        window_seconds=request.window_seconds,
        model_path=request.model_path,
        event_id=request.event_id,
        minute=request.minute,
        second=request.second,
        player_name=request.player_name,
    )


def build_match_response(request: AnalyzeMatchRequest) -> Dict[str, Any]:
    base, events, players = analyze_match(request)
    top_n = request.top_n

    response = {
        **base,
        "players": _player_sections(players, top_n=top_n),
        "phases": _phase_records(events, top_n=top_n, min_improvement=request.min_improvement),
        "teamStats": {
            "decisionByType": _decision_type_stats(events),
            "timeline": _timeline_stats(events),
        },
    }
    response["summary"]["missedShotOrGoalOpportunities"] = int(
        len(response["phases"]["missedShotOrGoalOpportunities"])
    )
    return response


def build_phase_response(request: PhaseDecisionRequest) -> Dict[str, Any]:
    base, events, _ = analyze_match(request)
    filtered = events.copy()

    if request.event_id is not None:
        filtered = filtered[pd.to_numeric(filtered["event_id"], errors="coerce") == request.event_id]
    if request.minute is not None:
        filtered = filtered[pd.to_numeric(filtered["minute"], errors="coerce") == request.minute]
    if request.second is not None:
        filtered = filtered[pd.to_numeric(filtered["second"], errors="coerce") == request.second]
    if request.player_name:
        filtered = filtered[filtered["player_name"].astype(str).str.lower() == request.player_name.strip().lower()]

    if len(filtered) == 0:
        raise HTTPException(status_code=404, detail="No phase matched the provided filters.")

    selected = filtered.sort_values(["potentialGain", "decisionValue"], ascending=[False, True]).iloc[0]
    alternatives = [
        {"decision": "pass", "predictedValue": float(selected["pred_pass"])},
        {"decision": "shot", "predictedValue": float(selected["pred_shot"])},
        {"decision": "carry", "predictedValue": float(selected["pred_carry"])},
    ]
    alternatives = sorted(alternatives, key=lambda x: x["predictedValue"], reverse=True)

    actual_decision = str(selected["decision"])
    best_decision = str(selected["bestDecisionType"])
    potential_gain = float(selected["potentialGain"])
    insight = (
        "Decizia reala este deja cea mai buna pentru aceasta faza."
        if actual_decision == best_decision or potential_gain <= 0.0
        else f"Modelul estimeaza ca '{best_decision}' era mai buna decat '{actual_decision}' (+{potential_gain:.4f})."
    )

    payload = {
        **base,
        "phaseDecision": {
            "eventId": _to_int(selected["event_id"]),
            "minute": _to_int(selected["minute"]),
            "second": _to_int(selected["second"]),
            "playerName": str(selected["player_name"]),
            "teamName": str(selected["team_name"]),
            "actualDecision": actual_decision,
            "actualDecisionValue": round(float(selected["decisionValue"]), 4),
            "bestDecision": best_decision,
            "bestDecisionValue": round(float(selected["bestDecisionValue"]), 4),
            "potentialGain": round(potential_gain, 4),
            "isLowDecision": bool(selected["isLowDecision"]),
            "suggestedAlternative": None if pd.isna(selected["suggestedAlternative"]) else str(selected["suggestedAlternative"]),
            "actualShotOnTarget": bool(selected["actualShotOnTarget"]),
            "actualGoal": bool(selected["actualGoal"]),
            "alternatives": [
                {"decision": item["decision"], "predictedValue": round(float(item["predictedValue"]), 4)}
                for item in alternatives
            ],
            "insight": insight,
            "matchedRows": int(len(filtered)),
        },
    }
    return payload


app = FastAPI(
    title="Decision Quality API",
    version="1.0.0",
    description=(
        "API pentru analiza calitatii deciziilor in fotbal. "
        "Primeste JSON de meci (Wyscout-style) si returneaza insight-uri pe faze si jucatori."
    ),
)


@app.get("/health", tags=["system"], summary="Health Check")
def health():
    model_exists = Path(DEFAULT_MODEL_PATH).exists()
    return {
        "status": "ok",
        "modelFile": str(DEFAULT_MODEL_PATH),
        "modelExists": model_exists,
    }


@app.post(
    "/api/v1/matches/analyze",
    tags=["analysis"],
    summary="Analyze Match (JSON Body)",
    description="Analizeaza meciul primit in JSON body (Wyscout-style) si returneaza statistici complete.",
)
def analyze_match_endpoint(request: AnalyzeMatchRequest):
    return build_match_response(request)


@app.post("/api/v1/matches/analyze/upload")
async def analyze_match_upload_endpoint(
    file: UploadFile = File(..., description="Wyscout-style match JSON file."),
    match_id: Optional[int] = Form(None),
    team_name: Optional[str] = Form(None),
    low_score_quantile: float = Form(0.25),
    min_improvement: float = Form(0.02),
    min_player_actions: int = Form(8),
    top_n: int = Form(10),
    window_seconds: int = Form(10),
    model_path: str = Form(str(DEFAULT_MODEL_PATH)),
):
    payload = await _parse_uploaded_json_file(file)
    request = _build_analyze_request(
        payload=payload,
        match_id=match_id,
        team_name=team_name,
        low_score_quantile=low_score_quantile,
        min_improvement=min_improvement,
        min_player_actions=min_player_actions,
        top_n=top_n,
        window_seconds=window_seconds,
        model_path=model_path,
    )
    return build_match_response(request)


@app.post(
    "/api/v1/matches/players/insights",
    tags=["analysis"],
    summary="Players Insights (JSON Body)",
    description="Returneaza doar insight-uri pe jucatori pentru meciul primit in JSON body.",
)
def analyze_players_endpoint(request: AnalyzeMatchRequest):
    base, _, players = analyze_match(request)
    return {
        **base,
        "players": _player_sections(players, top_n=request.top_n),
    }


@app.post("/api/v1/matches/players/insights/upload")
async def analyze_players_upload_endpoint(
    file: UploadFile = File(..., description="Wyscout-style match JSON file."),
    match_id: Optional[int] = Form(None),
    team_name: Optional[str] = Form(None),
    low_score_quantile: float = Form(0.25),
    min_improvement: float = Form(0.02),
    min_player_actions: int = Form(8),
    top_n: int = Form(10),
    window_seconds: int = Form(10),
    model_path: str = Form(str(DEFAULT_MODEL_PATH)),
):
    payload = await _parse_uploaded_json_file(file)
    request = _build_analyze_request(
        payload=payload,
        match_id=match_id,
        team_name=team_name,
        low_score_quantile=low_score_quantile,
        min_improvement=min_improvement,
        min_player_actions=min_player_actions,
        top_n=top_n,
        window_seconds=window_seconds,
        model_path=model_path,
    )
    base, _, players = analyze_match(request)
    return {
        **base,
        "players": _player_sections(players, top_n=request.top_n),
    }


@app.post(
    "/api/v1/matches/phases/decision",
    tags=["analysis"],
    summary="Phase Decision (JSON Body)",
    description="Pentru o faza specifica, estimeaza cea mai buna decizie (pass/shot/carry).",
)
def phase_decision_endpoint(request: PhaseDecisionRequest):
    return build_phase_response(request)


@app.post("/api/v1/matches/phases/decision/upload")
async def phase_decision_upload_endpoint(
    file: UploadFile = File(..., description="Wyscout-style match JSON file."),
    event_id: Optional[int] = Form(None),
    minute: Optional[int] = Form(None),
    second: Optional[int] = Form(None),
    player_name: Optional[str] = Form(None),
    match_id: Optional[int] = Form(None),
    team_name: Optional[str] = Form(None),
    low_score_quantile: float = Form(0.25),
    min_improvement: float = Form(0.02),
    min_player_actions: int = Form(8),
    top_n: int = Form(10),
    window_seconds: int = Form(10),
    model_path: str = Form(str(DEFAULT_MODEL_PATH)),
):
    payload = await _parse_uploaded_json_file(file)
    request = _build_phase_request(
        payload=payload,
        match_id=match_id,
        team_name=team_name,
        low_score_quantile=low_score_quantile,
        min_improvement=min_improvement,
        min_player_actions=min_player_actions,
        top_n=top_n,
        window_seconds=window_seconds,
        model_path=model_path,
        event_id=event_id,
        minute=minute,
        second=second,
        player_name=player_name,
    )
    return build_phase_response(request)


@app.post(
    "/api/v1/demo/matches/analyze",
    tags=["demo"],
    summary="Demo Analyze Match (No Upload Needed)",
    description=(
        "Endpoint pentru test rapid din /docs. Foloseste un fisier JSON local de sample "
        "(default: u_cluj_10_matches_wyscout_events_combined.json)."
    ),
)
def demo_analyze_match_endpoint(request: AnalyzeMatchDemoRequest):
    analyze_request = _build_analyze_request_from_demo(request)
    return build_match_response(analyze_request)


@app.post(
    "/api/v1/demo/matches/players/insights",
    tags=["demo"],
    summary="Demo Players Insights (No Upload Needed)",
    description="Endpoint demo pentru test rapid in /docs, folosind JSON local de sample.",
)
def demo_players_endpoint(request: AnalyzeMatchDemoRequest):
    analyze_request = _build_analyze_request_from_demo(request)
    base, _, players = analyze_match(analyze_request)
    return {
        **base,
        "players": _player_sections(players, top_n=analyze_request.top_n),
    }


@app.post(
    "/api/v1/demo/matches/phases/decision",
    tags=["demo"],
    summary="Demo Phase Decision (No Upload Needed)",
    description="Endpoint demo pentru analiza unei faze specifice, direct din /docs.",
)
def demo_phase_decision_endpoint(request: PhaseDecisionDemoRequest):
    phase_request = _build_phase_request_from_demo(request)
    return build_phase_response(phase_request)


@app.get("/api/v1/model/info", tags=["system"], summary="Model Info")
def model_info(model_path: str = str(DEFAULT_MODEL_PATH)):
    report_path = Path("u_cluj_decision_quality_model_report.json")
    payload = {
        "modelPath": model_path,
        "modelExists": Path(model_path).exists(),
        "reportPath": str(report_path),
        "reportExists": report_path.exists(),
    }
    if report_path.exists():
        payload["report"] = json.loads(report_path.read_text(encoding="utf-8"))
    return payload
