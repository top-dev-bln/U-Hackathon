from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .io_loader import IngestionResult

BASE_COLUMNS: tuple[str, ...] = (
    "source_file",
    "source_file_path",
    "player_id",
    "match_id",
    "competition_id",
    "season_id",
    "round_id",
    "team_id",
    "positions_count",
    "position_codes",
    "position_names",
    "primary_position_code",
    "primary_position_name",
    "primary_position_percent",
    "minutes_on_field",
)


@dataclass
class PlayerFlattenResult:
    fieldnames: list[str]
    rows: list[dict[str, Any]]
    players_seen: int
    rows_filtered_minutes_lte_zero: int
    rows_with_missing_match_id: int
    invalid_source_files: int

    def build_report_payload(self, ingestion_result: IngestionResult) -> dict[str, Any]:
        row_match_ids = {row["match_id"] for row in self.rows if isinstance(row.get("match_id"), int)}
        expected_match_ids = set(ingestion_result.unique_match_ids)
        missing_expected_match_ids = sorted(expected_match_ids - row_match_ids)

        total_columns = [col for col in self.fieldnames if col.startswith("total_")]
        average_columns = [col for col in self.fieldnames if col.startswith("average_")]
        percent_columns = [col for col in self.fieldnames if col.startswith("percent_")]

        return {
            "totals": {
                "input_valid_files": len(ingestion_result.valid_records),
                "input_invalid_files": self.invalid_source_files,
                "players_seen_before_filters": self.players_seen,
                "rows_after_filters": len(self.rows),
                "rows_filtered_minutes_lte_zero": self.rows_filtered_minutes_lte_zero,
                "rows_with_missing_match_id": self.rows_with_missing_match_id,
                "unique_match_ids_in_output": len(row_match_ids),
                "output_columns": len(self.fieldnames),
            },
            "consistency_checks": {
                "rows_gt_zero": len(self.rows) > 0,
                "all_rows_have_match_id": self.rows_with_missing_match_id == 0,
                "missing_expected_match_ids_count": len(missing_expected_match_ids),
                "missing_expected_match_ids": missing_expected_match_ids,
            },
            "column_groups": {
                "base_columns": list(BASE_COLUMNS),
                "total_columns_count": len(total_columns),
                "average_columns_count": len(average_columns),
                "percent_columns_count": len(percent_columns),
            },
        }


def build_player_level_rows(cfg: PipelineConfig, ingestion_result: IngestionResult) -> PlayerFlattenResult:
    rows: list[dict[str, Any]] = []
    dynamic_columns: set[str] = set()
    players_seen = 0
    rows_filtered_minutes_lte_zero = 0
    rows_with_missing_match_id = 0
    invalid_source_files = 0

    for record in ingestion_result.valid_records:
        parsed = _read_json_object(Path(record.file_path))
        if not isinstance(parsed, dict):
            invalid_source_files += 1
            continue

        players = parsed.get("players")
        if not isinstance(players, list):
            invalid_source_files += 1
            continue

        for player in players:
            if not isinstance(player, dict):
                continue

            players_seen += 1
            row = _extract_base_row(player, record.file_name, record.file_path)
            if row["match_id"] is None:
                rows_with_missing_match_id += 1

            minutes_on_field = row.get("minutes_on_field")
            if isinstance(minutes_on_field, (int, float)) and float(minutes_on_field) <= 0:
                rows_filtered_minutes_lte_zero += 1
                continue

            _flatten_metric_group(player.get("total"), "total", row, dynamic_columns)
            _flatten_metric_group(player.get("average"), "average", row, dynamic_columns)
            _flatten_metric_group(player.get("percent"), "percent", row, dynamic_columns)
            rows.append(row)

    fieldnames = list(BASE_COLUMNS) + sorted(dynamic_columns)
    _normalize_numeric_columns(rows, fieldnames)

    return PlayerFlattenResult(
        fieldnames=fieldnames,
        rows=rows,
        players_seen=players_seen,
        rows_filtered_minutes_lte_zero=rows_filtered_minutes_lte_zero,
        rows_with_missing_match_id=rows_with_missing_match_id,
        invalid_source_files=invalid_source_files,
    )


def write_player_level_csv(output_path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serialized = {
                key: _serialize_for_csv(row.get(key))
                for key in fieldnames
            }
            writer.writerow(serialized)


def _extract_base_row(player: dict[str, Any], file_name: str, file_path: str) -> dict[str, Any]:
    position_payload = player.get("positions") if isinstance(player.get("positions"), list) else []
    (
        positions_count,
        position_codes,
        position_names,
        primary_position_code,
        primary_position_name,
        primary_position_percent,
    ) = _extract_positions(position_payload)

    return {
        "source_file": file_name,
        "source_file_path": file_path,
        "player_id": _normalize_scalar(player.get("playerId")),
        "match_id": _normalize_scalar(player.get("matchId")),
        "competition_id": _normalize_scalar(player.get("competitionId")),
        "season_id": _normalize_scalar(player.get("seasonId")),
        "round_id": _normalize_scalar(player.get("roundId")),
        "team_id": _normalize_scalar(player.get("teamId")),
        "positions_count": positions_count,
        "position_codes": position_codes,
        "position_names": position_names,
        "primary_position_code": primary_position_code,
        "primary_position_name": primary_position_name,
        "primary_position_percent": _normalize_scalar(primary_position_percent),
        "minutes_on_field": _extract_minutes_on_field(player),
    }


def _extract_positions(
    positions: list[Any],
) -> tuple[int, str, str, str | None, str | None, int | float | None]:
    codes: list[str] = []
    names: list[str] = []
    best_code: str | None = None
    best_name: str | None = None
    best_percent: float | None = None

    for item in positions:
        if not isinstance(item, dict):
            continue
        position = item.get("position")
        if not isinstance(position, dict):
            continue

        code = position.get("code")
        name = position.get("name")
        percent = _normalize_scalar(item.get("percent"))

        if isinstance(code, str) and code:
            codes.append(code)
        if isinstance(name, str) and name:
            names.append(name)

        if isinstance(percent, (int, float)):
            if best_percent is None or float(percent) > best_percent:
                best_percent = float(percent)
                best_code = code if isinstance(code, str) else None
                best_name = name if isinstance(name, str) else None

    primary_percent: int | float | None
    if best_percent is None:
        primary_percent = None
    elif best_percent.is_integer():
        primary_percent = int(best_percent)
    else:
        primary_percent = best_percent

    return (
        len(positions),
        "|".join(codes),
        "|".join(names),
        best_code,
        best_name,
        primary_percent,
    )


def _extract_minutes_on_field(player: dict[str, Any]) -> int | float | None:
    candidates = [
        player.get("minutesOnField"),
        _dict_get(player.get("total"), "minutesOnField"),
        _dict_get(player.get("average"), "minutesOnField"),
        _dict_get(player.get("total"), "minutesPlayed"),
        _dict_get(player.get("average"), "minutesPlayed"),
    ]
    for candidate in candidates:
        normalized = _normalize_scalar(candidate)
        if isinstance(normalized, (int, float)):
            return normalized
    return None


def _dict_get(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return None


def _flatten_metric_group(
    group_payload: Any,
    prefix: str,
    row: dict[str, Any],
    dynamic_columns: set[str],
) -> None:
    if not isinstance(group_payload, dict):
        return

    for key, raw_value in group_payload.items():
        column_name = f"{prefix}_{key}"
        normalized_value = _normalize_scalar(raw_value)
        if normalized_value is None and raw_value is not None:
            continue
        row[column_name] = normalized_value
        dynamic_columns.add(column_name)


def _normalize_numeric_columns(rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    for column in fieldnames:
        numeric_values: list[float] = []
        has_non_numeric = False

        for row in rows:
            value = row.get(column)
            if value is None:
                continue
            if isinstance(value, bool):
                numeric_values.append(float(int(value)))
                continue
            if isinstance(value, int):
                numeric_values.append(float(value))
                continue
            if isinstance(value, float):
                if math.isfinite(value):
                    numeric_values.append(value)
                    continue
                row[column] = None
                continue
            has_non_numeric = True
            break

        if has_non_numeric or not numeric_values:
            continue

        should_be_int = all(val.is_integer() for val in numeric_values)
        for row in rows:
            value = row.get(column)
            if value is None:
                continue
            if not isinstance(value, (int, float, bool)):
                continue
            row[column] = int(value) if should_be_int else float(value)


def _normalize_scalar(value: Any) -> int | float | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None

        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            try:
                return int(stripped)
            except ValueError:
                return stripped
        try:
            parsed_float = float(stripped)
            if math.isfinite(parsed_float):
                return parsed_float
            return None
        except ValueError:
            return stripped
    return None


def _serialize_for_csv(value: Any) -> str | int | float:
    if value is None:
        return ""
    return value


def _read_json_object(file_path: Path) -> dict[str, Any] | None:
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = file_path.read_text(encoding="utf-8-sig")
        except Exception:
            return None
    except Exception:
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return parsed
    return None
