from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .anomaly import build_anomaly_scores, write_anomaly_scores_csv
from .baseline import build_league_baseline
from .clustering import build_tactical_clusters
from .comparator import build_u_cluj_comparisons
from .config import PipelineConfig, default_config
from .feature_engineering import build_team_match_features
from .flatten_players import build_player_level_rows, write_player_level_csv
from .io_loader import load_players_stats
from .insights import build_u_cluj_tactical_weakness_report
from .report_builder import build_u_cluj_final_report
from .team_aggregate import build_team_match_dataset, write_team_match_csv

LOGGER = logging.getLogger("tactical_baseline")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def run_pipeline(config: PipelineConfig | None = None) -> dict[str, Path]:
    cfg = config or default_config()
    configure_logging()

    LOGGER.info("Starting tactical baseline pipeline (M0 + M10 with strict/heuristic sensitivity).")
    LOGGER.info("Active config: %s", cfg.as_dict())

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Ensured output directory exists: %s", cfg.output_dir)

    ingestion_result = load_players_stats(cfg)
    report_payload = ingestion_result.as_report_payload(cfg)
    report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()

    report_path = cfg.output_dir / cfg.load_report_filename
    _write_json(report_path, report_payload)

    LOGGER.info(
        "M1 ingestion summary: discovered=%s valid=%s invalid=%s unique_match_ids=%s",
        report_payload["totals"]["discovered_files"],
        report_payload["totals"]["valid_files"],
        report_payload["totals"]["invalid_files"],
        report_payload["totals"]["unique_match_ids"],
    )
    LOGGER.info("Load report written to: %s", report_path)

    player_flatten_result = build_player_level_rows(cfg, ingestion_result)
    player_level_csv_path = cfg.output_dir / cfg.player_level_csv_filename
    write_player_level_csv(player_level_csv_path, player_flatten_result.fieldnames, player_flatten_result.rows)

    player_level_report_path = cfg.output_dir / cfg.player_level_report_filename
    player_level_report_payload = player_flatten_result.build_report_payload(ingestion_result)
    player_level_report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(player_level_report_path, player_level_report_payload)

    LOGGER.info(
        (
            "M2 flatten summary: players_seen=%s rows_after_filters=%s "
            "filtered_minutes_lte_zero=%s missing_match_id_rows=%s output_columns=%s"
        ),
        player_flatten_result.players_seen,
        len(player_flatten_result.rows),
        player_flatten_result.rows_filtered_minutes_lte_zero,
        player_flatten_result.rows_with_missing_match_id,
        len(player_flatten_result.fieldnames),
    )
    LOGGER.info("Player level dataset written to: %s", player_level_csv_path)
    LOGGER.info("Player level report written to: %s", player_level_report_path)

    team_match_heuristic_result = build_team_match_dataset(
        player_rows=player_flatten_result.rows,
        player_fieldnames=player_flatten_result.fieldnames,
        team_assignment_mode="heuristic",
    )
    team_match_strict_result = build_team_match_dataset(
        player_rows=player_flatten_result.rows,
        player_fieldnames=player_flatten_result.fieldnames,
        team_assignment_mode="strict",
    )

    team_match_heuristic_csv_path = cfg.output_dir / cfg.team_match_heuristic_csv_filename
    write_team_match_csv(
        team_match_heuristic_csv_path,
        team_match_heuristic_result.fieldnames,
        team_match_heuristic_result.rows,
    )
    team_match_strict_csv_path = cfg.output_dir / cfg.team_match_strict_csv_filename
    write_team_match_csv(
        team_match_strict_csv_path,
        team_match_strict_result.fieldnames,
        team_match_strict_result.rows,
    )

    team_match_heuristic_report_path = cfg.output_dir / cfg.team_match_heuristic_report_filename
    team_match_heuristic_report_payload = dict(team_match_heuristic_result.report_payload)
    team_match_heuristic_report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(team_match_heuristic_report_path, team_match_heuristic_report_payload)

    team_match_strict_report_path = cfg.output_dir / cfg.team_match_strict_report_filename
    team_match_strict_report_payload = dict(team_match_strict_result.report_payload)
    team_match_strict_report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(team_match_strict_report_path, team_match_strict_report_payload)

    sensitivity_report_payload = _build_team_assignment_sensitivity_report(
        heuristic_rows=team_match_heuristic_result.rows,
        strict_rows=team_match_strict_result.rows,
    )
    sensitivity_report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    sensitivity_report_path = cfg.output_dir / cfg.team_assignment_sensitivity_report_filename
    _write_json(sensitivity_report_path, sensitivity_report_payload)

    selected_mode = cfg.team_assignment_mode.strip().lower()
    if selected_mode not in {"heuristic", "strict"}:
        raise ValueError(
            f"Invalid team_assignment_mode={cfg.team_assignment_mode!r}. Expected 'heuristic' or 'strict'."
        )
    selected_result = team_match_heuristic_result if selected_mode == "heuristic" else team_match_strict_result

    team_match_csv_path = cfg.output_dir / cfg.team_match_csv_filename
    write_team_match_csv(team_match_csv_path, selected_result.fieldnames, selected_result.rows)

    team_match_report_path = cfg.output_dir / cfg.team_match_report_filename
    selected_report_payload = dict(selected_result.report_payload)
    selected_report_payload["selected_mode"] = selected_mode
    selected_report_payload["recommended_mode_from_sensitivity"] = sensitivity_report_payload["recommended_mode"]
    selected_report_payload["recommendation_rule"] = sensitivity_report_payload["decision_rule"]
    selected_report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(team_match_report_path, selected_report_payload)

    team_features_result = build_team_match_features(
        team_rows=selected_result.rows,
        team_fieldnames=selected_result.fieldnames,
    )
    team_match_features_csv_path = cfg.output_dir / cfg.team_match_features_csv_filename
    write_team_match_csv(
        team_match_features_csv_path,
        team_features_result.fieldnames,
        team_features_result.rows,
    )
    team_match_features_report_path = cfg.output_dir / cfg.team_match_features_report_filename
    team_match_features_report_payload = dict(team_features_result.report_payload)
    team_match_features_report_payload["team_assignment_mode"] = selected_mode
    team_match_features_report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(team_match_features_report_path, team_match_features_report_payload)

    metric_directions_path = cfg.output_dir / cfg.metric_directions_filename
    metric_directions_payload = {
        "team_assignment_mode": selected_mode,
        "metric_directions": team_features_result.metric_directions,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(metric_directions_path, metric_directions_payload)

    metric_names = list(team_features_result.metric_directions.keys())
    baseline_result = build_league_baseline(
        feature_rows=team_features_result.rows,
        metric_names=metric_names,
        team_assignment_mode=selected_mode,
    )
    league_baseline_payload = dict(baseline_result.baseline_payload)
    league_baseline_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    league_baseline_path = cfg.output_dir / cfg.league_baseline_filename
    _write_json(league_baseline_path, league_baseline_payload)

    league_distributions_payload = dict(baseline_result.distributions_payload)
    league_distributions_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    league_distributions_path = cfg.output_dir / cfg.league_distributions_filename
    _write_json(league_distributions_path, league_distributions_payload)

    u_cluj_comparisons_result = build_u_cluj_comparisons(
        team_feature_rows=team_features_result.rows,
        league_baseline_payload=league_baseline_payload,
        league_distributions_payload=league_distributions_payload,
        metric_directions=team_features_result.metric_directions,
        u_cluj_aliases=list(cfg.u_cluj_team_aliases),
        team_assignment_mode=selected_mode,
    )
    u_cluj_match_comparisons_payload = dict(u_cluj_comparisons_result.comparisons_payload)
    u_cluj_match_comparisons_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    u_cluj_match_comparisons_path = cfg.output_dir / cfg.u_cluj_match_comparisons_filename
    _write_json(u_cluj_match_comparisons_path, u_cluj_match_comparisons_payload)

    u_cluj_weakness_result = build_u_cluj_tactical_weakness_report(
        comparisons_payload=u_cluj_match_comparisons_payload,
        team_feature_rows=team_features_result.rows,
        max_insights_per_match=cfg.max_insights_per_match,
        team_assignment_mode=selected_mode,
    )
    u_cluj_rule_based_insights_payload = dict(u_cluj_weakness_result.report_payload)
    u_cluj_rule_based_insights_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    u_cluj_rule_based_insights_path = cfg.output_dir / cfg.u_cluj_rule_based_insights_filename
    _write_json(u_cluj_rule_based_insights_path, u_cluj_rule_based_insights_payload)

    anomaly_result = build_anomaly_scores(
        team_feature_rows=team_features_result.rows,
        u_cluj_aliases=list(cfg.u_cluj_team_aliases),
        team_assignment_mode=selected_mode,
        contamination=cfg.anomaly_contamination,
        random_state=cfg.anomaly_random_state,
        n_estimators=cfg.anomaly_n_estimators,
    )
    anomaly_scores_path = cfg.output_dir / cfg.anomaly_scores_csv_filename
    write_anomaly_scores_csv(anomaly_scores_path, anomaly_result.fieldnames, anomaly_result.rows)
    anomaly_report_payload = dict(anomaly_result.report_payload)
    anomaly_report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    anomaly_report_path = cfg.output_dir / cfg.anomaly_report_filename
    _write_json(anomaly_report_path, anomaly_report_payload)

    tactical_clusters_result = build_tactical_clusters(
        team_feature_rows=team_features_result.rows,
        u_cluj_aliases=list(cfg.u_cluj_team_aliases),
        team_assignment_mode=selected_mode,
        n_clusters=cfg.kmeans_n_clusters,
        random_state=cfg.kmeans_random_state,
        n_init=cfg.kmeans_n_init,
    )
    tactical_clusters_payload = dict(tactical_clusters_result.clusters_payload)
    tactical_clusters_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    tactical_clusters_path = cfg.output_dir / cfg.tactical_clusters_filename
    _write_json(tactical_clusters_path, tactical_clusters_payload)

    tactical_clusters_report_payload = dict(tactical_clusters_result.report_payload)
    tactical_clusters_report_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    tactical_clusters_report_path = cfg.output_dir / cfg.tactical_clusters_report_filename
    _write_json(tactical_clusters_report_path, tactical_clusters_report_payload)

    final_report_result = build_u_cluj_final_report(
        comparisons_payload=u_cluj_match_comparisons_payload,
        insights_payload=u_cluj_rule_based_insights_payload,
        anomaly_rows=anomaly_result.rows,
        tactical_clusters_payload=tactical_clusters_payload,
        team_assignment_mode=selected_mode,
    )
    u_cluj_tactical_weakness_payload = dict(final_report_result.payload)
    u_cluj_tactical_weakness_payload["run_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    u_cluj_tactical_weakness_path = cfg.output_dir / cfg.u_cluj_tactical_weakness_report_filename
    _write_json(u_cluj_tactical_weakness_path, u_cluj_tactical_weakness_payload)

    sanity_checks = {
        "smoke_run_end_to_end": True,
        "match_id_present_player_rows": all(
            _to_int_or_none(row.get("match_id")) is not None for row in player_flatten_result.rows
        ),
        "match_id_present_team_rows": all(
            _to_int_or_none(row.get("match_id")) is not None for row in selected_result.rows
        ),
        "unique_team_match_key": len(selected_result.rows)
        == len(
            {
                (
                    _to_int_or_none(row.get("match_id")),
                    _to_int_or_none(row.get("team_id")),
                )
                for row in selected_result.rows
            }
        ),
        "finite_critical_metrics": _all_metrics_finite(
            rows=team_features_result.rows,
            metric_names=list(team_features_result.metric_directions.keys()),
        ),
    }
    sanity_passed = all(sanity_checks.values())
    sanity_report_payload = {
        "status": "passed" if sanity_passed else "failed",
        "checks": sanity_checks,
        "counts": {
            "input_stats_files_discovered": ingestion_result.discovered_files_count,
            "input_stats_files_valid": len(ingestion_result.valid_records),
            "player_rows": len(player_flatten_result.rows),
            "team_match_rows": len(selected_result.rows),
            "team_feature_rows": len(team_features_result.rows),
            "u_cluj_matches_final_report": u_cluj_tactical_weakness_payload["scope"]["matches_count"],
        },
        "team_assignment_mode": selected_mode,
        "critical_metrics_checked": list(team_features_result.metric_directions.keys()),
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    sanity_report_path = cfg.output_dir / cfg.sanity_report_filename
    _write_json(sanity_report_path, sanity_report_payload)

    LOGGER.info(
        (
            "M3 team aggregation summary: heuristic_rows=%s strict_rows=%s selected_mode=%s "
            "recommended_mode=%s"
        ),
        team_match_heuristic_report_payload["totals"]["output_team_match_rows"],
        team_match_strict_report_payload["totals"]["output_team_match_rows"],
        selected_mode,
        sensitivity_report_payload["recommended_mode"],
    )
    LOGGER.info("Team-match heuristic dataset written to: %s", team_match_heuristic_csv_path)
    LOGGER.info("Team-match strict dataset written to: %s", team_match_strict_csv_path)
    LOGGER.info("Team assignment sensitivity report written to: %s", sensitivity_report_path)
    LOGGER.info("Team-match dataset written to: %s", team_match_csv_path)
    LOGGER.info("Team-match report written to: %s", team_match_report_path)
    LOGGER.info(
        "M4 feature engineering summary: output_rows=%s derived_metrics=%s rows_with_nonfinite=%s",
        team_match_features_report_payload["totals"]["output_rows"],
        team_match_features_report_payload["totals"]["derived_metrics_count"],
        team_match_features_report_payload["validations"]["rows_with_nonfinite_values"],
    )
    LOGGER.info("Team-match features dataset written to: %s", team_match_features_csv_path)
    LOGGER.info("Team-match features report written to: %s", team_match_features_report_path)
    LOGGER.info("Metric directions written to: %s", metric_directions_path)
    LOGGER.info(
        "M5 baseline summary: metrics=%s rows=%s",
        league_baseline_payload["scope"]["metrics_count"],
        league_baseline_payload["scope"]["team_match_rows_used"],
    )
    LOGGER.info("League baseline written to: %s", league_baseline_path)
    LOGGER.info("League distributions written to: %s", league_distributions_path)
    LOGGER.info(
        "M6 comparator summary: u_cluj_matches=%s metrics=%s",
        u_cluj_match_comparisons_payload["scope"]["u_cluj_match_count"],
        u_cluj_match_comparisons_payload["scope"]["metric_count"],
    )
    LOGGER.info("U Cluj match comparisons written to: %s", u_cluj_match_comparisons_path)
    LOGGER.info(
        "M7 insights summary: matches=%s max_insights_per_match=%s",
        u_cluj_rule_based_insights_payload["scope"]["matches_analyzed"],
        u_cluj_rule_based_insights_payload["scope"]["max_insights_per_match"],
    )
    LOGGER.info("U Cluj rule-based insights written to: %s", u_cluj_rule_based_insights_path)
    LOGGER.info(
        "M8 anomaly summary: rows_scored=%s u_cluj_rows=%s u_cluj_anomalous=%s",
        anomaly_report_payload["totals"]["rows_scored"],
        anomaly_report_payload["totals"]["u_cluj_rows_scored"],
        anomaly_report_payload["totals"]["u_cluj_anomalous_rows"],
    )
    LOGGER.info("Anomaly scores written to: %s", anomaly_scores_path)
    LOGGER.info("Anomaly report written to: %s", anomaly_report_path)
    LOGGER.info(
        "M9 clustering summary: k=%s rows=%s clusters=%s",
        tactical_clusters_report_payload["model"]["k"],
        tactical_clusters_payload["scope"]["rows_used"],
        len(tactical_clusters_payload["clusters"]),
    )
    LOGGER.info("Tactical clusters written to: %s", tactical_clusters_path)
    LOGGER.info("Tactical clusters report written to: %s", tactical_clusters_report_path)
    LOGGER.info(
        "M10 final report summary: matches=%s",
        u_cluj_tactical_weakness_payload["scope"]["matches_count"],
    )
    LOGGER.info("U Cluj tactical weakness report written to: %s", u_cluj_tactical_weakness_path)
    LOGGER.info(
        "M11 sanity summary: status=%s checks_passed=%s/%s",
        sanity_report_payload["status"],
        sum(1 for v in sanity_checks.values() if v),
        len(sanity_checks),
    )
    LOGGER.info("Sanity report written to: %s", sanity_report_path)
    return {
        "load_report": report_path,
        "player_level_dataset": player_level_csv_path,
        "player_level_report": player_level_report_path,
        "team_match_dataset_heuristic": team_match_heuristic_csv_path,
        "team_match_dataset_strict": team_match_strict_csv_path,
        "team_match_report_heuristic": team_match_heuristic_report_path,
        "team_match_report_strict": team_match_strict_report_path,
        "team_assignment_sensitivity_report": sensitivity_report_path,
        "team_match_dataset": team_match_csv_path,
        "team_match_report": team_match_report_path,
        "team_match_features_dataset": team_match_features_csv_path,
        "team_match_features_report": team_match_features_report_path,
        "metric_directions": metric_directions_path,
        "league_baseline": league_baseline_path,
        "league_distributions": league_distributions_path,
        "u_cluj_match_comparisons": u_cluj_match_comparisons_path,
        "u_cluj_rule_based_insights": u_cluj_rule_based_insights_path,
        "u_cluj_tactical_weakness_report": u_cluj_tactical_weakness_path,
        "anomaly_scores": anomaly_scores_path,
        "anomaly_report": anomaly_report_path,
        "tactical_clusters": tactical_clusters_path,
        "tactical_clusters_report": tactical_clusters_report_path,
        "sanity_report": sanity_report_path,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_team_assignment_sensitivity_report(
    heuristic_rows: list[dict[str, Any]],
    strict_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    metrics = [
        "total_passes",
        "total_losses",
        "total_xgShot",
        "total_shots",
        "total_recoveries",
        "total_duels",
    ]
    threshold_percent = 3.0

    heuristic_by_key = _index_team_rows(heuristic_rows)
    strict_by_key = _index_team_rows(strict_rows)
    all_keys = sorted(set(heuristic_by_key) | set(strict_by_key))

    per_metric: dict[str, dict[str, float]] = {}
    worst_metric_mean_pct = 0.0

    key_diff_scores: list[tuple[tuple[int, int], float]] = []
    for key in all_keys:
        row_h = heuristic_by_key.get(key, {})
        row_s = strict_by_key.get(key, {})
        score = 0.0
        for metric in metrics:
            h_val = _to_float(row_h.get(metric))
            s_val = _to_float(row_s.get(metric))
            abs_diff = abs(h_val - s_val)
            denom = max(abs(s_val), 1.0)
            score += (abs_diff / denom) * 100.0
        key_diff_scores.append((key, score))

    for metric in metrics:
        abs_diffs: list[float] = []
        rel_diffs_pct: list[float] = []
        total_heuristic = 0.0
        total_strict = 0.0

        for key in all_keys:
            row_h = heuristic_by_key.get(key, {})
            row_s = strict_by_key.get(key, {})
            h_val = _to_float(row_h.get(metric))
            s_val = _to_float(row_s.get(metric))
            total_heuristic += h_val
            total_strict += s_val

            abs_diff = abs(h_val - s_val)
            abs_diffs.append(abs_diff)
            rel_diffs_pct.append((abs_diff / max(abs(s_val), 1.0)) * 100.0)

        mean_abs_diff = _safe_mean(abs_diffs)
        mean_rel_diff_pct = _safe_mean(rel_diffs_pct)
        max_rel_diff_pct = max(rel_diffs_pct) if rel_diffs_pct else 0.0
        worst_metric_mean_pct = max(worst_metric_mean_pct, mean_rel_diff_pct)

        per_metric[metric] = {
            "total_heuristic": total_heuristic,
            "total_strict": total_strict,
            "total_abs_diff": abs(total_heuristic - total_strict),
            "mean_abs_diff_per_team_match": mean_abs_diff,
            "mean_relative_diff_pct_per_team_match": mean_rel_diff_pct,
            "max_relative_diff_pct_per_team_match": max_rel_diff_pct,
        }

    recommended_mode = "heuristic" if worst_metric_mean_pct < threshold_percent else "strict"
    top_keys = sorted(key_diff_scores, key=lambda item: item[1], reverse=True)[:20]
    top_key_rows = [
        {
            "match_id": key[0],
            "team_id": key[1],
            "combined_relative_diff_score_pct": score,
        }
        for key, score in top_keys
    ]

    return {
        "threshold_percent": threshold_percent,
        "decision_rule": (
            "if max(mean_relative_diff_pct_per_team_match across key metrics) < threshold => heuristic else strict"
        ),
        "recommended_mode": recommended_mode,
        "worst_metric_mean_relative_diff_pct": worst_metric_mean_pct,
        "totals": {
            "team_match_rows_heuristic": len(heuristic_rows),
            "team_match_rows_strict": len(strict_rows),
            "comparable_team_match_keys": len(all_keys),
        },
        "metrics": per_metric,
        "top_sensitive_team_match_keys": top_key_rows,
    }


def _index_team_rows(rows: list[dict[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    indexed: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        match_id = _to_int(row.get("match_id"))
        team_id = _to_int(row.get("team_id"))
        if match_id is None or team_id is None:
            continue
        indexed[(match_id, team_id)] = row
    return indexed


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            try:
                return int(stripped)
            except ValueError:
                return None
    return None


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return 0.0
        try:
            return float(stripped)
        except ValueError:
            return 0.0
    return 0.0


def _safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _to_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            try:
                return int(stripped)
            except ValueError:
                return None
    return None


def _all_metrics_finite(rows: list[dict[str, Any]], metric_names: list[str]) -> bool:
    for row in rows:
        for metric in metric_names:
            value = row.get(metric)
            parsed = _to_float_or_none(value)
            if parsed is None:
                return False
            if not math.isfinite(parsed):
                return False
    return True


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None
