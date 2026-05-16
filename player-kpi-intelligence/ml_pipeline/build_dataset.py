from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import combine_player_stats as cps

DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
OVERRIDES_FILE = CONFIG_DIR / "manual_name_overrides.json"
QUALITY_REPORT_FILE = PROJECT_ROOT / "data_quality_report.md"
EXCLUDED_DEVICE_NAME_NORMS = {"raji"}

RATE_METRICS = {"distance_per_min", "power_metabolic_avg_wkg", "sprints_count_per_min"}
SUM_METRICS = [metric for metric in cps.DEVICE_METRIC_MAP.values() if metric not in RATE_METRICS]

MATCH_CONTEXT_FIELDS = [
    "matches_in_squad",
    "matches_played",
    "minutesOnField",
    "goals",
    "assists",
    "xgShot",
    "xgAssist",
    "shots",
    "shotsOnTarget",
    "passes",
    "successfulPasses",
    "duels",
    "duelsWon",
    "pass_accuracy_pct",
    "duel_win_rate_pct",
    "goals_per90",
    "assists_per90",
    "xg_per90",
    "xg_assist_per90",
    "shots_per90",
    "key_passes_per90",
]


def load_manual_overrides(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}

    out: dict[str, int] = {}
    for raw_name, raw_player_id in payload.items():
        if raw_player_id in (None, "", 0):
            continue
        try:
            out[cps.normalize_text(str(raw_name))] = int(raw_player_id)
        except (TypeError, ValueError):
            continue
    return out


def ensure_overrides_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    template = {
        "raji": None
    }
    path.write_text(json.dumps(template, indent=2), encoding="utf-8")


def as_date(value: str) -> date:
    return date.fromisoformat(value)


def quantile(values: Iterable[float], q: float) -> float:
    data = sorted(float(v) for v in values)
    if not data:
        return 0.0
    if q <= 0:
        return data[0]
    if q >= 1:
        return data[-1]
    idx = (len(data) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(data) - 1)
    frac = idx - lo
    return data[lo] * (1 - frac) + data[hi] * frac


def write_csv(path: Path, rows: list[dict[str, object]], preferred_start: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = set()
    for row in rows:
        keys.update(row.keys())
    ordered: list[str] = []
    if preferred_start:
        for key in preferred_start:
            if key in keys:
                ordered.append(key)
                keys.remove(key)
    ordered.extend(sorted(keys))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ordered)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_name_mapping_review(
    name_mapping: dict[str, dict[str, object]],
    player_catalog: dict[int, dict[str, object]],
    device_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    counts = defaultdict(int)
    for row in device_rows:
        counts[str(row["device_player_name"])] += 1

    out: list[dict[str, object]] = []
    for device_name, mapping_row in sorted(name_mapping.items()):
        candidate_ids = [x for x in str(mapping_row.get("candidate_ids", "")).split(",") if x]
        candidate_names = []
        for candidate_id in candidate_ids:
            try:
                player_id = int(candidate_id)
            except ValueError:
                continue
            player = player_catalog.get(player_id, {})
            full_name = str(player.get("full_name", "")).strip()
            short_name = str(player.get("short_name", "")).strip()
            if full_name or short_name:
                candidate_names.append(f"{player_id}:{short_name}|{full_name}")

        resolved_id = mapping_row.get("wy_id", "")
        if isinstance(resolved_id, int):
            resolved_player = player_catalog.get(resolved_id, {})
            resolved_short = resolved_player.get("short_name", "")
            resolved_full = resolved_player.get("full_name", "")
            resolved_role = resolved_player.get("role", "")
        else:
            resolved_short = ""
            resolved_full = ""
            resolved_role = ""

        out.append(
            {
                "device_player_name": device_name,
                "device_player_name_norm": mapping_row.get("device_player_name_norm", ""),
                "status": mapping_row.get("status", ""),
                "sessions_rows_count": counts[device_name],
                "candidate_ids": mapping_row.get("candidate_ids", ""),
                "candidate_names": " || ".join(candidate_names),
                "resolved_wy_id": resolved_id,
                "resolved_short_name": resolved_short,
                "resolved_full_name": resolved_full,
                "resolved_role": resolved_role,
            }
        )
    return out


def build_daily_table(
    enriched_device_rows: list[dict[str, object]],
    match_summary: dict[int, dict[str, object]],
    player_catalog: dict[int, dict[str, object]],
) -> list[dict[str, object]]:
    by_key: dict[tuple[int, str], dict[str, object]] = {}
    per_player_dates: dict[int, list[str]] = defaultdict(list)

    for row in enriched_device_rows:
        wy_id = row.get("wy_id")
        session_date = str(row.get("session_date", "")).strip()
        if not isinstance(wy_id, int):
            continue
        if not session_date:
            continue

        key = (wy_id, session_date)
        if key not in by_key:
            player = player_catalog.get(wy_id, {})
            by_key[key] = {
                "wy_id": wy_id,
                "date": session_date,
                "player_short_name": player.get("short_name", ""),
                "player_full_name": player.get("full_name", ""),
                "player_role": player.get("role", ""),
                "week_calendar": row.get("week_calendar", ""),
                "sessions_count": 0,
                "session_names": [],
                "_duration_for_rates": 0.0,
            }
            for metric in SUM_METRICS:
                by_key[key][metric] = 0.0
            for metric in RATE_METRICS:
                by_key[key][f"_{metric}_weighted_sum"] = 0.0
                by_key[key][metric] = 0.0
            per_player_dates[wy_id].append(session_date)

        target = by_key[key]
        target["sessions_count"] = int(target["sessions_count"]) + 1
        session_name = str(row.get("session_name", "")).strip()
        if session_name:
            target["session_names"].append(session_name)

        duration = cps.as_float(row.get("duration_min"))
        target["_duration_for_rates"] = cps.as_float(target["_duration_for_rates"]) + duration

        for metric in SUM_METRICS:
            target[metric] = cps.as_float(target[metric]) + cps.as_float(row.get(metric))
        for metric in RATE_METRICS:
            target[f"_{metric}_weighted_sum"] = cps.as_float(target[f"_{metric}_weighted_sum"]) + cps.as_float(
                row.get(metric)
            ) * duration

    daily_rows = list(by_key.values())
    daily_rows.sort(key=lambda r: (int(r["wy_id"]), str(r["date"])))

    days_since_prev: dict[tuple[int, str], int] = {}
    for player_id, date_values in per_player_dates.items():
        unique_dates = sorted(set(date_values))
        previous: date | None = None
        for date_value in unique_dates:
            current = as_date(date_value)
            if previous is None:
                days_since_prev[(player_id, date_value)] = 0
            else:
                days_since_prev[(player_id, date_value)] = (current - previous).days
            previous = current

    for row in daily_rows:
        wy_id = int(row["wy_id"])
        date_value = str(row["date"])
        duration_for_rates = cps.as_float(row["_duration_for_rates"])
        for metric in RATE_METRICS:
            weighted_sum = cps.as_float(row[f"_{metric}_weighted_sum"])
            row[metric] = weighted_sum / duration_for_rates if duration_for_rates > 0 else 0.0
            del row[f"_{metric}_weighted_sum"]
        del row["_duration_for_rates"]

        row["session_names"] = " || ".join(sorted(set(str(x) for x in row["session_names"])))
        row["weekday"] = as_date(date_value).weekday()
        row["week_number_iso"] = as_date(date_value).isocalendar().week
        row["days_since_prev_session"] = days_since_prev.get((wy_id, date_value), 0)

        row["high_speed_distance_m"] = cps.as_float(row["speed_20_25_m"]) + cps.as_float(row["speed_25_50_m"])
        distance_total = cps.as_float(row["distance_m"])
        row["high_speed_share_pct"] = row["high_speed_distance_m"] / distance_total * 100 if distance_total else 0.0
        row["training_load_proxy"] = distance_total * cps.as_float(row["power_metabolic_avg_wkg"])
        row["accel_total_count"] = (
            cps.as_float(row["accel_pos_3_4_count"])
            + cps.as_float(row["accel_pos_4_10_count"])
            + cps.as_float(row["accel_neg_4_3_count"])
            + cps.as_float(row["accel_neg_10_4_count"])
        )

        match_row = match_summary.get(wy_id, {})
        for field in MATCH_CONTEXT_FIELDS:
            row[f"match_{field}"] = cps.as_float(match_row.get(field))

        row["match_day_flag"] = 0
        row["days_since_match"] = ""

    return daily_rows


def build_quality_report(
    device_rows: list[dict[str, object]],
    enriched_device_rows: list[dict[str, object]],
    name_mapping_rows: list[dict[str, object]],
    daily_rows: list[dict[str, object]],
) -> str:
    mapped_device_rows = sum(1 for row in enriched_device_rows if isinstance(row.get("wy_id"), int))
    mapping_coverage = (mapped_device_rows / len(enriched_device_rows) * 100) if enriched_device_rows else 0.0
    unique_players = len({int(row["wy_id"]) for row in daily_rows})

    unresolved = [row for row in name_mapping_rows if str(row.get("status")) == "unmatched"]
    missing_session_date = sum(1 for row in enriched_device_rows if not str(row.get("session_date", "")).strip())

    keys = [(int(row["wy_id"]), str(row["date"])) for row in daily_rows]
    duplicates = len(keys) - len(set(keys))

    distance_values = [cps.as_float(row.get("distance_m")) for row in daily_rows]
    duration_values = [cps.as_float(row.get("duration_min")) for row in daily_rows]
    q99_distance = quantile(distance_values, 0.99)
    q99_duration = quantile(duration_values, 0.99)
    outlier_distance_count = sum(1 for value in distance_values if value > q99_distance * 1.5)
    outlier_duration_count = sum(1 for value in duration_values if value > q99_duration * 1.5)

    if daily_rows:
        min_date = min(str(row["date"]) for row in daily_rows)
        max_date = max(str(row["date"]) for row in daily_rows)
    else:
        min_date = ""
        max_date = ""

    lines = [
        "# Data Quality Report",
        "",
        "## Snapshot",
        f"- Device session rows: {len(device_rows)}",
        f"- Device rows with mapped wy_id: {mapped_device_rows} ({mapping_coverage:.2f}%)",
        f"- Distinct device names: {len(name_mapping_rows)}",
        f"- Unmatched device names: {len(unresolved)}",
        f"- Daily rows in player_day_features: {len(daily_rows)}",
        f"- Distinct players in player_day_features: {unique_players}",
        f"- Date range in player_day_features: {min_date} -> {max_date}",
        "",
        "## Integrity Checks",
        f"- Duplicate keys on (wy_id, date): {duplicates}",
        f"- Device rows with missing parsed session_date: {missing_session_date}",
        "",
        "## Outlier Scan (simple threshold q99*1.5)",
        f"- Distance daily q99: {q99_distance:.2f}, outliers: {outlier_distance_count}",
        f"- Duration daily q99: {q99_duration:.2f}, outliers: {outlier_duration_count}",
        "",
        "## Unmatched Names",
    ]
    if unresolved:
        for row in unresolved:
            lines.append(f"- {row['device_player_name']} (rows={row['sessions_rows_count']})")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Notes / Limitations",
            "- Match JSON files do not contain explicit match date fields in this dataset.",
            "- match_day_flag and days_since_match are placeholders until match dates are added.",
            "- For this phase, match metrics are player-level season aggregates joined on wy_id.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    ensure_overrides_template(OVERRIDES_FILE)
    manual_overrides = load_manual_overrides(OVERRIDES_FILE)
    cps.MANUAL_DEVICE_NAME_OVERRIDES.clear()
    cps.MANUAL_DEVICE_NAME_OVERRIDES.update(manual_overrides)

    player_catalog = cps.load_player_catalog()
    match_rows = cps.read_match_rows()
    match_summary = cps.aggregate_match_rows(match_rows)
    device_rows = cps.read_device_rows()
    device_rows = [
        row for row in device_rows if str(row.get("device_player_name_norm", "")).strip() not in EXCLUDED_DEVICE_NAME_NORMS
    ]
    unique_device_names = {str(row["device_player_name"]) for row in device_rows}
    name_mapping = cps.map_device_names(unique_device_names, player_catalog, match_summary)
    enriched_device_rows = cps.enrich_device_rows_with_mapping(device_rows, name_mapping, player_catalog)

    name_mapping_rows = build_name_mapping_review(name_mapping, player_catalog, device_rows)
    daily_rows = build_daily_table(enriched_device_rows, match_summary, player_catalog)
    quality_report = build_quality_report(device_rows, enriched_device_rows, name_mapping_rows, daily_rows)

    write_csv(
        DATA_DIR / "name_mapping_review.csv",
        name_mapping_rows,
        preferred_start=[
            "device_player_name",
            "status",
            "sessions_rows_count",
            "candidate_ids",
            "candidate_names",
            "resolved_wy_id",
            "resolved_short_name",
            "resolved_full_name",
            "resolved_role",
        ],
    )
    write_csv(
        DATA_DIR / "device_sessions_enriched.csv",
        enriched_device_rows,
        preferred_start=[
            "source_file",
            "source_sheet",
            "session_date",
            "session_name",
            "week_calendar",
            "device_player_name",
            "mapping_status",
            "wy_id",
            "player_short_name",
            "player_full_name",
        ],
    )
    write_csv(
        DATA_DIR / "player_day_features.csv",
        daily_rows,
        preferred_start=[
            "date",
            "wy_id",
            "player_short_name",
            "player_full_name",
            "player_role",
            "sessions_count",
            "distance_m",
            "duration_min",
            "distance_per_min",
            "high_speed_distance_m",
            "high_speed_share_pct",
            "training_load_proxy",
            "days_since_prev_session",
            "weekday",
            "week_number_iso",
        ],
    )
    QUALITY_REPORT_FILE.write_text(quality_report, encoding="utf-8")

    unresolved = [row for row in name_mapping_rows if row["status"] == "unmatched"]
    print(f"manual overrides applied: {len(manual_overrides)}")
    print(f"device rows: {len(device_rows)}")
    print(f"daily rows: {len(daily_rows)}")
    print(f"distinct players (daily): {len({row['wy_id'] for row in daily_rows})}")
    print(f"unmatched names: {len(unresolved)}")
    if unresolved:
        for row in unresolved:
            print(f"- {row['device_player_name']}")
    print(f"wrote: {DATA_DIR / 'player_day_features.csv'}")
    print(f"wrote: {DATA_DIR / 'name_mapping_review.csv'}")
    print(f"wrote: {QUALITY_REPORT_FILE}")


if __name__ == "__main__":
    main()
