from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import PipelineConfig


@dataclass
class FileLoadIssue:
    file_path: str
    reason: str
    details: str | None = None


@dataclass
class MatchFileRecord:
    file_name: str
    file_path: str
    match_id: int
    players_count: int


@dataclass
class IngestionResult:
    discovered_files_count: int
    valid_records: list[MatchFileRecord]
    errors: list[FileLoadIssue]

    @property
    def unique_match_ids(self) -> list[int]:
        return sorted({record.match_id for record in self.valid_records})

    def as_report_payload(self, cfg: PipelineConfig) -> dict[str, Any]:
        parse_or_read_errors = sum(
            1 for err in self.errors if err.reason in {"json_parse_error", "file_read_error"}
        )
        schema_errors = len(self.errors) - parse_or_read_errors
        max_error_examples = max(cfg.max_error_examples, 0)

        return {
            "config": cfg.as_dict(),
            "totals": {
                "discovered_files": self.discovered_files_count,
                "valid_files": len(self.valid_records),
                "invalid_files": len(self.errors),
                "parse_or_read_errors": parse_or_read_errors,
                "schema_errors": schema_errors,
                "unique_match_ids": len(self.unique_match_ids),
            },
            "unique_match_ids": self.unique_match_ids,
            "valid_files": [asdict(record) for record in self.valid_records],
            "error_examples": [asdict(err) for err in self.errors[:max_error_examples]],
        }


def discover_players_stats_files(cfg: PipelineConfig) -> list[Path]:
    if cfg.recursive_input_scan:
        candidates = cfg.input_dir.rglob(cfg.input_glob)
    else:
        candidates = cfg.input_dir.glob(cfg.input_glob)

    files = [path for path in candidates if path.is_file() and path.name.endswith("_players_stats.json")]
    files.sort(key=lambda p: str(p).casefold())
    return files


def load_players_stats(cfg: PipelineConfig) -> IngestionResult:
    records: list[MatchFileRecord] = []
    errors: list[FileLoadIssue] = []
    input_files = discover_players_stats_files(cfg)

    for file_path in input_files:
        data, load_err = _read_json(file_path)
        if load_err is not None:
            errors.append(load_err)
            continue

        assert data is not None  # narrowed by load_err check
        record, schema_err = _validate_and_extract(file_path, data, cfg)
        if schema_err is not None:
            errors.append(schema_err)
            continue

        assert record is not None  # narrowed by schema_err check
        records.append(record)

    return IngestionResult(
        discovered_files_count=len(input_files),
        valid_records=records,
        errors=errors,
    )


def _read_json(file_path: Path) -> tuple[dict[str, Any] | None, FileLoadIssue | None]:
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = file_path.read_text(encoding="utf-8-sig")
        except Exception as exc:  # pragma: no cover - defensive fallback
            return None, FileLoadIssue(
                file_path=str(file_path),
                reason="file_read_error",
                details=str(exc),
            )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return None, FileLoadIssue(
            file_path=str(file_path),
            reason="file_read_error",
            details=str(exc),
        )

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, FileLoadIssue(
            file_path=str(file_path),
            reason="json_parse_error",
            details=str(exc),
        )

    if not isinstance(parsed, dict):
        return None, FileLoadIssue(
            file_path=str(file_path),
            reason="schema_error",
            details="Top-level JSON must be an object.",
        )
    return parsed, None


def _validate_and_extract(
    file_path: Path, data: dict[str, Any], cfg: PipelineConfig
) -> tuple[MatchFileRecord | None, FileLoadIssue | None]:
    missing_keys = [key for key in cfg.mandatory_top_level_keys if key not in data]
    if missing_keys:
        return None, FileLoadIssue(
            file_path=str(file_path),
            reason="schema_error",
            details=f"Missing top-level keys: {missing_keys}",
        )

    players = data.get("players")
    if not isinstance(players, list) or len(players) == 0:
        return None, FileLoadIssue(
            file_path=str(file_path),
            reason="schema_error",
            details="Field 'players' must be a non-empty list.",
        )

    match_ids: set[int] = set()
    for idx, player in enumerate(players):
        if not isinstance(player, dict):
            return None, FileLoadIssue(
                file_path=str(file_path),
                reason="schema_error",
                details=f"Player at index {idx} is not an object.",
            )

        missing_player_keys = [key for key in cfg.mandatory_player_keys if key not in player]
        if missing_player_keys:
            return None, FileLoadIssue(
                file_path=str(file_path),
                reason="schema_error",
                details=f"Player at index {idx} missing keys: {missing_player_keys}",
            )

        match_id_value = player.get("matchId")
        if not isinstance(match_id_value, int):
            return None, FileLoadIssue(
                file_path=str(file_path),
                reason="schema_error",
                details=f"Player at index {idx} has invalid matchId={match_id_value!r}",
            )
        match_ids.add(match_id_value)

    if len(match_ids) != 1:
        return None, FileLoadIssue(
            file_path=str(file_path),
            reason="schema_error",
            details=f"Expected a single matchId per file, got {sorted(match_ids)}",
        )

    match_id = next(iter(match_ids))
    return (
        MatchFileRecord(
            file_name=file_path.name,
            file_path=str(file_path),
            match_id=match_id,
            players_count=len(players),
        ),
        None,
    )
