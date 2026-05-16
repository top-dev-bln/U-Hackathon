from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEEKLY_FILE = PROJECT_ROOT / "outputs" / "player_kpi_weekly.csv"
DAILY_FILE = PROJECT_ROOT / "outputs" / "player_kpi_daily.csv"

NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
INT_RE = re.compile(r"^-?\d+$")


def parse_scalar(value: str) -> Any:
    raw = value.strip()
    if raw == "":
        return None
    if INT_RE.match(raw):
        try:
            return int(raw)
        except ValueError:
            return raw
    if NUMBER_RE.match(raw):
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{k: parse_scalar(v or "") for k, v in row.items()} for row in reader]


def pick_source(cadence: Literal["weekly", "daily"]) -> Path:
    if cadence == "weekly":
        return WEEKLY_FILE
    return DAILY_FILE


def latest_per_player(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[int, dict[str, Any]] = {}
    for row in rows:
        player_id = int(row.get("wy_id") or 0)
        row_date = str(row.get("date") or "")
        previous = latest.get(player_id)
        if previous is None or row_date > str(previous.get("date") or ""):
            latest[player_id] = row
    out = list(latest.values())
    out.sort(key=lambda x: int(x.get("wy_id") or 0))
    return out


app = FastAPI(title="Player KPI API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/players")
def get_players(
    cadence: Literal["weekly", "daily"] = Query(default="weekly"),
    latest_only: bool = Query(default=False),
    as_of_date: str | None = Query(default=None, description="YYYY-MM-DD"),
) -> dict[str, Any]:
    source = pick_source(cadence)
    rows = load_rows(source)

    if as_of_date:
        try:
            _ = date.fromisoformat(as_of_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid as_of_date, expected YYYY-MM-DD")
        rows = [row for row in rows if str(row.get("date") or "") == as_of_date]

    if latest_only:
        rows = latest_per_player(rows)

    return {
        "cadence": cadence,
        "source_file": str(source.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "rows_count": len(rows),
        "data": rows,
    }
