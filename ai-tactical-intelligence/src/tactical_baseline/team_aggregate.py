from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MATCH_FILENAME_SUFFIX = "_players_stats.json"


@dataclass(frozen=True)
class MatchContext:
    home_team: str
    away_team: str
    score_home: int
    score_away: int


@dataclass
class TeamAggregationResult:
    fieldnames: list[str]
    rows: list[dict[str, Any]]
    report_payload: dict[str, Any]


def build_team_match_dataset(
    player_rows: list[dict[str, Any]],
    player_fieldnames: list[str],
    *,
    team_assignment_mode: str = "heuristic",
) -> TeamAggregationResult:
    mode = team_assignment_mode.strip().lower()
    if mode not in {"heuristic", "strict"}:
        raise ValueError(f"Unsupported team_assignment_mode={team_assignment_mode!r}. Use 'heuristic' or 'strict'.")

    total_metric_columns = [name for name in player_fieldnames if name.startswith("total_")]
    match_context_by_file: dict[str, MatchContext] = {}
    parse_errors: list[str] = []

    for row in player_rows:
        source_file = _as_text(row.get("source_file"))
        if not source_file or source_file in match_context_by_file:
            continue
        match_ctx = _parse_match_context_from_filename(source_file)
        if match_ctx is None:
            parse_errors.append(source_file)
            continue
        match_context_by_file[source_file] = match_ctx

    player_team_candidates = _build_player_team_candidates(player_rows, match_context_by_file)
    resolved_player_team = {
        player_id: next(iter(candidates))
        for player_id, candidates in player_team_candidates.items()
        if len(candidates) == 1
    }

    team_names = sorted(
        {
            ctx.home_team
            for ctx in match_context_by_file.values()
        }
        | {
            ctx.away_team
            for ctx in match_context_by_file.values()
        },
        key=str.casefold,
    )
    team_name_to_id = {name: idx + 1 for idx, name in enumerate(team_names)}

    rows_by_match: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in player_rows:
        match_id = _as_int(row.get("match_id"))
        if match_id is None:
            continue
        rows_by_match[match_id].append(row)

    assignment_method_counts = Counter()
    unassigned_rows = 0
    rows_dropped_strict_mode = 0
    skipped_rows_bad_filename = 0
    aggregate_by_key: dict[tuple[int, int], dict[str, Any]] = {}
    teams_per_match: dict[int, set[int]] = defaultdict(set)

    for match_id, match_rows in rows_by_match.items():
        source_file = _as_text(match_rows[0].get("source_file"))
        match_ctx = match_context_by_file.get(source_file) if source_file else None
        if match_ctx is None:
            skipped_rows_bad_filename += len(match_rows)
            continue

        pair = (match_ctx.home_team, match_ctx.away_team)
        assignment_by_row_index: dict[int, tuple[str, str]] = {}
        team_counts = Counter()
        unresolved_indices: list[int] = []

        for idx, row in enumerate(match_rows):
            explicit_team_name = _extract_explicit_team_name_from_row(row, pair)
            if explicit_team_name is not None:
                assignment_by_row_index[idx] = (explicit_team_name, "explicit_team_id")
                team_counts[explicit_team_name] += 1
                continue

            player_id = _as_int(row.get("player_id"))
            inferred_team = resolved_player_team.get(player_id) if player_id is not None else None
            if inferred_team in pair:
                assignment_by_row_index[idx] = (inferred_team, "player_intersection")
                team_counts[inferred_team] += 1
            else:
                unresolved_indices.append(idx)

        if mode == "heuristic":
            for idx in unresolved_indices:
                chosen_team = pair[0] if team_counts[pair[0]] <= team_counts[pair[1]] else pair[1]
                assignment_by_row_index[idx] = (chosen_team, "match_balance_fallback")
                team_counts[chosen_team] += 1
        else:
            rows_dropped_strict_mode += len(unresolved_indices)

        for idx, row in enumerate(match_rows):
            assignment = assignment_by_row_index.get(idx)
            if assignment is None:
                unassigned_rows += 1
                continue

            team_name, assignment_method = assignment
            team_id = team_name_to_id[team_name]
            assignment_method_counts[assignment_method] += 1

            agg_key = (match_id, team_id)
            if agg_key not in aggregate_by_key:
                aggregate_by_key[agg_key] = _init_team_row(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=team_name,
                    match_ctx=match_ctx,
                    total_metric_columns=total_metric_columns,
                )

            target = aggregate_by_key[agg_key]
            target["players_count"] += 1
            target["players_assignment_explicit_team_id"] += int(assignment_method == "explicit_team_id")
            target["players_assignment_player_intersection"] += int(assignment_method == "player_intersection")
            target["players_assignment_match_balance_fallback"] += int(
                assignment_method == "match_balance_fallback"
            )

            minutes = _as_float(row.get("minutes_on_field"))
            if minutes is not None:
                target["minutes_on_field_sum"] += minutes

            for column in total_metric_columns:
                value = _as_float(row.get(column))
                if value is not None:
                    target[column] += value

            teams_per_match[match_id].add(team_id)

    output_rows = [aggregate_by_key[key] for key in sorted(aggregate_by_key)]
    _finalize_numeric_types(output_rows, total_metric_columns)

    fieldnames = [
        "match_id",
        "team_id",
        "team_name",
        "home_team_name",
        "away_team_name",
        "home_score",
        "away_score",
        "is_home_team",
        "players_count",
        "players_assignment_explicit_team_id",
        "players_assignment_player_intersection",
        "players_assignment_match_balance_fallback",
        "minutes_on_field_sum",
    ] + total_metric_columns

    matches_with_over_two = sorted(match_id for match_id, teams in teams_per_match.items() if len(teams) > 2)
    matches_with_under_two = sorted(match_id for match_id, teams in teams_per_match.items() if len(teams) < 2)
    unique_key_check = len(output_rows) == len({(row["match_id"], row["team_id"]) for row in output_rows})

    report_payload = {
        "team_assignment_mode": mode,
        "totals": {
            "input_player_rows": len(player_rows),
            "output_team_match_rows": len(output_rows),
            "matches_in_output": len(teams_per_match),
            "distinct_teams": len(team_name_to_id),
            "match_filename_parse_errors": len(set(parse_errors)),
            "rows_skipped_bad_filename": skipped_rows_bad_filename,
            "rows_unassigned": unassigned_rows,
            "rows_dropped_strict_mode": rows_dropped_strict_mode,
        },
        "assignment_methods": dict(assignment_method_counts),
        "validations": {
            "unique_match_team_key": unique_key_check,
            "matches_with_more_than_two_teams_count": len(matches_with_over_two),
            "matches_with_less_than_two_teams_count": len(matches_with_under_two),
            "matches_with_more_than_two_teams": matches_with_over_two[:25],
            "matches_with_less_than_two_teams": matches_with_under_two[:25],
        },
        "team_id_mapping": [
            {"team_id": team_name_to_id[name], "team_name": name}
            for name in team_names
        ],
    }

    return TeamAggregationResult(fieldnames=fieldnames, rows=output_rows, report_payload=report_payload)


def write_team_match_csv(output_path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: _serialize_csv_value(row.get(name)) for name in fieldnames})


def _parse_match_context_from_filename(file_name: str) -> MatchContext | None:
    if not file_name.endswith(MATCH_FILENAME_SUFFIX):
        return None

    stem = file_name[: -len(".json")]
    if not stem.endswith("_players_stats"):
        return None

    core = stem[: -len("_players_stats")]
    id_suffix_match = re.search(r"_(\d+)$", core)
    if id_suffix_match is not None:
        core = core[: id_suffix_match.start()]

    if "," not in core:
        return None

    matchup_part, score_part = core.rsplit(",", 1)
    matchup_part = matchup_part.strip()
    score_part = score_part.strip()
    score_match = re.match(r"^(\d+)\s*-\s*(\d+)$", score_part)
    if score_match is None:
        return None
    if " - " not in matchup_part:
        return None

    home_team, away_team = matchup_part.split(" - ", 1)
    home_team = _normalize_team_name(home_team)
    away_team = _normalize_team_name(away_team)
    if not home_team or not away_team:
        return None

    return MatchContext(
        home_team=home_team,
        away_team=away_team,
        score_home=int(score_match.group(1)),
        score_away=int(score_match.group(2)),
    )


def _build_player_team_candidates(
    rows: list[dict[str, Any]],
    match_context_by_file: dict[str, MatchContext],
) -> dict[int, set[str]]:
    player_candidates: dict[int, set[str]] = {}
    for row in rows:
        player_id = _as_int(row.get("player_id"))
        source_file = _as_text(row.get("source_file"))
        if player_id is None or not source_file:
            continue

        match_ctx = match_context_by_file.get(source_file)
        if match_ctx is None:
            continue

        pair = {match_ctx.home_team, match_ctx.away_team}
        if player_id not in player_candidates:
            player_candidates[player_id] = set(pair)
        else:
            player_candidates[player_id].intersection_update(pair)
    return player_candidates


def _extract_explicit_team_name_from_row(row: dict[str, Any], pair: tuple[str, str]) -> str | None:
    # The current dataset does not provide team_id per player row, but keep this hook
    # for future inputs where team_id becomes available and can be mapped reliably.
    _ = row
    _ = pair
    return None


def _init_team_row(
    match_id: int,
    team_id: int,
    team_name: str,
    match_ctx: MatchContext,
    total_metric_columns: list[str],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "match_id": match_id,
        "team_id": team_id,
        "team_name": team_name,
        "home_team_name": match_ctx.home_team,
        "away_team_name": match_ctx.away_team,
        "home_score": match_ctx.score_home,
        "away_score": match_ctx.score_away,
        "is_home_team": int(team_name == match_ctx.home_team),
        "players_count": 0,
        "players_assignment_explicit_team_id": 0,
        "players_assignment_player_intersection": 0,
        "players_assignment_match_balance_fallback": 0,
        "minutes_on_field_sum": 0.0,
    }
    for metric in total_metric_columns:
        row[metric] = 0.0
    return row


def _finalize_numeric_types(rows: list[dict[str, Any]], total_metric_columns: list[str]) -> None:
    numeric_columns = [
        "minutes_on_field_sum",
        *total_metric_columns,
    ]
    for row in rows:
        for column in numeric_columns:
            value = row.get(column)
            if isinstance(value, float) and value.is_integer():
                row[column] = int(value)


def _normalize_team_name(value: str) -> str:
    return " ".join(value.strip().split())


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed == "":
            return None
        if trimmed.isdigit() or (trimmed.startswith("-") and trimmed[1:].isdigit()):
            try:
                return int(trimmed)
            except ValueError:
                return None
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed == "":
            return None
        try:
            return float(trimmed)
        except ValueError:
            return None
    return None


def _serialize_csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value
