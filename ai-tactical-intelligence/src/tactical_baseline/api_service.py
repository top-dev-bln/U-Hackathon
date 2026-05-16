from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .anomaly import build_anomaly_scores
from .clustering import build_tactical_clusters
from .comparator import build_u_cluj_comparisons
from .config import default_config
from .feature_engineering import build_team_match_features
from .insights import build_u_cluj_tactical_weakness_report
from .report_builder import build_u_cluj_final_report


@dataclass
class MatchRequestPayload:
    players_stats: dict[str, Any]
    home_team_name: str
    away_team_name: str
    match_id: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    focus_team_name: str | None = None


class TacticalInsightsService:
    def __init__(self, project_root: Path | None = None) -> None:
        self.cfg = default_config(project_root=project_root)
        self.outputs_dir = self.cfg.output_dir
        self._synthetic_match_counter = 900000000

        self.league_baseline = self._read_json(self.outputs_dir / self.cfg.league_baseline_filename)
        self.league_distributions = self._read_json(self.outputs_dir / self.cfg.league_distributions_filename)
        self.metric_directions = self._read_json(self.outputs_dir / self.cfg.metric_directions_filename).get(
            "metric_directions", {}
        )
        self.precomputed_final_report = self._read_json(
            self.outputs_dir / self.cfg.u_cluj_tactical_weakness_report_filename
        )
        self.precomputed_clusters = self._read_json(self.outputs_dir / self.cfg.tactical_clusters_filename)

        self.training_feature_rows = self._read_csv_rows(self.outputs_dir / self.cfg.team_match_features_csv_filename)
        self.existing_match_ids = {
            self._to_int(row.get("match_id"))
            for row in self.training_feature_rows
            if self._to_int(row.get("match_id")) is not None
        }

        self.total_metric_columns = sorted(
            {
                key
                for row in self.training_feature_rows[:1]
                for key in row.keys()
                if key.startswith("total_")
            }
        )
        if not self.total_metric_columns:
            # Fallback if header inspection above fails (e.g. empty rows)
            sample_rows = self._read_csv_rows(self.outputs_dir / self.cfg.team_match_csv_filename)
            self.total_metric_columns = sorted(
                {
                    key
                    for row in sample_rows[:1]
                    for key in row.keys()
                    if key.startswith("total_")
                }
            )

        team_match_report = self._read_json(self.outputs_dir / self.cfg.team_match_report_filename)
        self.team_name_to_id = {
            item["team_name"]: int(item["team_id"])
            for item in team_match_report.get("team_id_mapping", [])
            if isinstance(item, dict) and "team_name" in item and "team_id" in item
        }
        self.max_known_team_id = max(self.team_name_to_id.values(), default=100)
        self.player_team_lookup = self._build_player_team_lookup(
            self.outputs_dir / self.cfg.player_level_csv_filename
        )

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "team_assignment_mode": self.cfg.team_assignment_mode,
            "training_rows": len(self.training_feature_rows),
            "precomputed_matches": len(self.precomputed_final_report.get("matches", [])),
        }

    def get_league_baseline(self) -> dict[str, Any]:
        return self.league_baseline

    def get_league_distributions(self) -> dict[str, Any]:
        return self.league_distributions

    def get_precomputed_match_report(self, match_id: int) -> dict[str, Any] | None:
        for match in self.precomputed_final_report.get("matches", []):
            if self._to_int(match.get("matchId")) == match_id:
                return match
        return None

    def get_precomputed_tactical_profile(self, match_id: int) -> list[dict[str, Any]]:
        rows = []
        for row in self.precomputed_clusters.get("matches", []):
            if self._to_int(row.get("matchId")) == match_id:
                rows.append(row)
        return rows

    def build_live_match_report(self, payload: MatchRequestPayload) -> dict[str, Any]:
        match_id = self._resolve_match_id(payload.match_id, payload.players_stats)
        home_team = payload.home_team_name.strip()
        away_team = payload.away_team_name.strip()
        focus_aliases = self._resolve_focus_aliases(payload.focus_team_name, home_team, away_team)
        team_rows = self._build_team_rows_from_players_stats(
            players_stats=payload.players_stats,
            match_id=match_id,
            home_team_name=home_team,
            away_team_name=away_team,
            home_score=payload.home_score,
            away_score=payload.away_score,
        )

        feature_result = build_team_match_features(
            team_rows=team_rows,
            team_fieldnames=list(team_rows[0].keys()) if team_rows else [],
        )
        comparisons_result = build_u_cluj_comparisons(
            team_feature_rows=feature_result.rows,
            league_baseline_payload=self.league_baseline,
            league_distributions_payload=self.league_distributions,
            metric_directions=self.metric_directions,
            u_cluj_aliases=[home_team, away_team],
            team_assignment_mode=self.cfg.team_assignment_mode,
        )
        insights_result = build_u_cluj_tactical_weakness_report(
            comparisons_payload=comparisons_result.comparisons_payload,
            team_feature_rows=feature_result.rows,
            max_insights_per_match=self.cfg.max_insights_per_match,
            team_assignment_mode=self.cfg.team_assignment_mode,
        )

        rows_for_models = list(self.training_feature_rows) + feature_result.rows
        anomaly_result = build_anomaly_scores(
            team_feature_rows=rows_for_models,
            u_cluj_aliases=focus_aliases,
            team_assignment_mode=self.cfg.team_assignment_mode,
            contamination=self.cfg.anomaly_contamination,
            random_state=self.cfg.anomaly_random_state,
            n_estimators=self.cfg.anomaly_n_estimators,
        )
        anomaly_rows_for_match = [
            row for row in anomaly_result.rows if self._to_int(row.get("match_id")) == match_id
        ]

        cluster_result = build_tactical_clusters(
            team_feature_rows=rows_for_models,
            u_cluj_aliases=focus_aliases,
            team_assignment_mode=self.cfg.team_assignment_mode,
            n_clusters=self.cfg.kmeans_n_clusters,
            random_state=self.cfg.kmeans_random_state,
            n_init=self.cfg.kmeans_n_init,
        )
        tactical_clusters_for_match = {
            "scope": cluster_result.clusters_payload.get("scope", {}),
            "clusters": cluster_result.clusters_payload.get("clusters", []),
            "matches": [
                row
                for row in cluster_result.clusters_payload.get("matches", [])
                if self._to_int(row.get("matchId")) == match_id
            ],
        }

        final_report = build_u_cluj_final_report(
            comparisons_payload=comparisons_result.comparisons_payload,
            insights_payload=insights_result.report_payload,
            anomaly_rows=anomaly_rows_for_match,
            tactical_clusters_payload=tactical_clusters_for_match,
            team_assignment_mode=self.cfg.team_assignment_mode,
        ).payload

        if payload.focus_team_name:
            focus_norm = self._normalize_name(payload.focus_team_name)
            final_report["matches"] = [
                match
                for match in final_report.get("matches", [])
                if self._normalize_name(self._as_text(match.get("teamName")) or "") == focus_norm
            ]
            final_report["scope"]["matches_count"] = len(final_report["matches"])

        return {
            "inputMatchId": match_id,
            "teamAssignmentMode": self.cfg.team_assignment_mode,
            "teams": {"home": home_team, "away": away_team},
            "finalReport": final_report,
            "comparisons": comparisons_result.comparisons_payload,
            "ruleBasedInsights": insights_result.report_payload,
            "anomalyRowsForMatch": anomaly_rows_for_match,
            "tacticalClustersForMatch": tactical_clusters_for_match,
        }

    def build_live_match_report_compact(
        self,
        payload: MatchRequestPayload,
        *,
        top_insights: int = 2,
        top_strengths: int = 2,
    ) -> dict[str, Any]:
        live = self.build_live_match_report(payload)
        target = self._select_target_match(live, payload.focus_team_name)
        comparisons_row = self._find_comparison_row(
            live,
            match_id=self._to_int(target.get("matchId")),
            team_id=self._to_int(target.get("teamId")),
        )
        comparisons = comparisons_row.get("comparisons", {}) if isinstance(comparisons_row, dict) else {}

        team_name = self._as_text(target.get("teamName")) or ""
        home_team_name = self._as_text(target.get("homeTeamName")) or ""
        away_team_name = self._as_text(target.get("awayTeamName")) or ""
        is_home_team = bool(self._to_int(target.get("isHomeTeam")) == 1)
        opponent = away_team_name if is_home_team else home_team_name

        compact = {
            "match": {
                "matchId": self._to_int(target.get("matchId")),
                "teamName": team_name,
                "opponent": opponent,
                "isHomeTeam": is_home_team,
            },
            "summary": {
                "overallWeaknessScore": self._round_optional(self._to_float_or_none(target.get("overallWeaknessScore"))),
                "riskLevel": target.get("riskLevel"),
                "tacticalProfile": target.get("tacticalProfile"),
                "anomalyScore": self._round_optional(self._to_float_or_none(target.get("anomalyScore"))),
                "isAnomalous": bool(target.get("isAnomalous")),
            },
            "topInsights": self._compact_top_insights(target.get("insights", []), top_n=top_insights),
            "weaknessBreakdown": self._compact_weakness_breakdown(target.get("weaknessBreakdown", {})),
            "strengths": self._compact_strengths(comparisons, top_n=top_strengths),
        }
        return compact

    def build_live_match_report_detailed(self, payload: MatchRequestPayload) -> dict[str, Any]:
        live = self.build_live_match_report(payload)
        target = self._select_target_match(live, payload.focus_team_name)
        comparisons_row = self._find_comparison_row(
            live,
            match_id=self._to_int(target.get("matchId")),
            team_id=self._to_int(target.get("teamId")),
        )
        comparisons = comparisons_row.get("comparisons", {}) if isinstance(comparisons_row, dict) else {}

        detailed = {
            "matchId": self._to_int(target.get("matchId")),
            "teamId": self._to_int(target.get("teamId")),
            "teamName": target.get("teamName"),
            "baselineModel": {
                "overallWeaknessScore": self._round_optional(self._to_float_or_none(target.get("overallWeaknessScore"))),
                "riskLevel": target.get("riskLevel"),
                "tacticalProfile": target.get("tacticalProfile"),
                "clusterId": self._to_int(target.get("clusterId")),
                "anomalyScore": self._round_optional(self._to_float_or_none(target.get("anomalyScore"))),
                "isAnomalous": bool(target.get("isAnomalous")),
            },
            "weaknessSignals": self._build_weakness_signals(
                target.get("insights", []),
                comparisons,
            ),
            "metricComparisons": self._build_metric_comparisons_for_ml(comparisons),
        }
        return detailed

    def _resolve_focus_aliases(self, focus_team_name: str | None, home_team_name: str, away_team_name: str) -> list[str]:
        focus = self._as_text(focus_team_name)
        if focus:
            return [focus]

        detected = [
            team_name
            for team_name in (home_team_name, away_team_name)
            if self._is_probable_u_cluj_name(team_name)
        ]
        if detected:
            return detected

        # Fallback for generic match analysis when no explicit focus can be inferred.
        return [home_team_name, away_team_name]

    def _is_probable_u_cluj_name(self, team_name: str) -> bool:
        normalized_team = self._normalize_name(team_name)
        configured_aliases = {self._normalize_name(alias) for alias in self.cfg.u_cluj_team_aliases}
        if normalized_team in configured_aliases:
            return True
        return "cluj" in normalized_team and ("universit" in normalized_team or normalized_team == "u cluj")

    def _select_target_match(self, live_payload: dict[str, Any], focus_team_name: str | None) -> dict[str, Any]:
        final_report = live_payload.get("finalReport", {})
        matches = final_report.get("matches", []) if isinstance(final_report, dict) else []
        valid_matches = [row for row in matches if isinstance(row, dict)]
        if not valid_matches:
            raise ValueError("No match rows available in finalReport.")

        focus = self._as_text(focus_team_name)
        if focus:
            focus_norm = self._normalize_name(focus)
            for row in valid_matches:
                team_name = self._as_text(row.get("teamName")) or ""
                if self._normalize_name(team_name) == focus_norm:
                    return row

        if len(valid_matches) == 1:
            return valid_matches[0]

        for row in valid_matches:
            team_name = self._as_text(row.get("teamName")) or ""
            if self._is_probable_u_cluj_name(team_name):
                return row

        raise ValueError("Multiple team rows available. Set focus_team_name to select a single team.")

    def _find_comparison_row(
        self,
        live_payload: dict[str, Any],
        *,
        match_id: int | None,
        team_id: int | None,
    ) -> dict[str, Any]:
        comparisons = live_payload.get("comparisons", {})
        rows = comparisons.get("matches", []) if isinstance(comparisons, dict) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            mk = self._to_int(row.get("matchId"))
            tk = self._to_int(row.get("teamId"))
            if mk == match_id and tk == team_id:
                return row
        return {}

    def _compact_top_insights(self, insights: Any, *, top_n: int) -> list[dict[str, Any]]:
        if not isinstance(insights, list):
            return []
        out: list[dict[str, Any]] = []
        for insight in insights:
            if not isinstance(insight, dict):
                continue
            evidence = insight.get("evidence", {})
            evidence = evidence if isinstance(evidence, dict) else {}
            out.append(
                {
                    "type": insight.get("type"),
                    "severity": insight.get("severity"),
                    "title": insight.get("title"),
                    "message": insight.get("message"),
                    "metric": evidence.get("metric"),
                    "value": self._round_optional(self._to_float_or_none(evidence.get("value"))),
                    "leagueAverage": self._round_optional(self._to_float_or_none(evidence.get("leagueAverage"))),
                    "percentile": self._round_optional(self._to_float_or_none(evidence.get("percentile")), digits=2),
                    "recommendation": insight.get("recommendation"),
                }
            )
        limit = max(1, int(top_n))
        return out[:limit]

    def _compact_weakness_breakdown(self, breakdown: Any) -> dict[str, float]:
        source = breakdown if isinstance(breakdown, dict) else {}
        return {
            "buildUp": self._round_optional(self._to_float_or_none(source.get("buildUpWeaknessScore"))) or 0.0,
            "ballLoss": self._round_optional(self._to_float_or_none(source.get("ballLossWeaknessScore"))) or 0.0,
            "finalThird": self._round_optional(self._to_float_or_none(source.get("finalThirdWeaknessScore"))) or 0.0,
            "pressing": self._round_optional(self._to_float_or_none(source.get("pressingWeaknessScore"))) or 0.0,
            "duels": self._round_optional(self._to_float_or_none(source.get("duelWeaknessScore"))) or 0.0,
        }

    def _compact_strengths(self, comparisons: Any, *, top_n: int) -> list[dict[str, Any]]:
        source = comparisons if isinstance(comparisons, dict) else {}
        candidates: list[tuple[float, dict[str, Any]]] = []
        for metric_name, comp in source.items():
            if not isinstance(comp, dict):
                continue
            status = self._as_text(comp.get("status")) or ""
            if status not in {"strong", "very_strong"}:
                continue
            z_score = self._to_float_or_none(comp.get("zScore"))
            strength_score = abs(z_score) if z_score is not None else 0.0
            candidates.append(
                (
                    strength_score,
                    {
                        "metric": metric_name,
                        "label": self._metric_label(metric_name),
                        "value": self._round_optional(self._to_float_or_none(comp.get("value"))),
                        "leagueAverage": self._round_optional(self._to_float_or_none(comp.get("leagueAverage"))),
                        "status": status,
                    },
                )
            )
        candidates.sort(key=lambda item: item[0], reverse=True)
        limit = max(1, int(top_n))
        return [item[1] for item in candidates[:limit]]

    def _build_weakness_signals(self, insights: Any, comparisons: Any) -> list[dict[str, Any]]:
        insights_list = insights if isinstance(insights, list) else []
        comparisons_map = comparisons if isinstance(comparisons, dict) else {}
        out: list[dict[str, Any]] = []

        for insight in insights_list:
            if not isinstance(insight, dict):
                continue
            evidence = insight.get("evidence", {})
            evidence = evidence if isinstance(evidence, dict) else {}
            metric = self._as_text(evidence.get("metric"))
            comp = comparisons_map.get(metric, {}) if metric else {}
            comp = comp if isinstance(comp, dict) else {}
            signal_id = f"{self._as_text(insight.get('type')) or 'unknown'}.{self._slug(self._as_text(insight.get('title')) or 'signal')}"

            out.append(
                {
                    "signalId": signal_id,
                    "category": insight.get("type"),
                    "severityScore": self._round_optional(self._to_float_or_none(insight.get("severityScore"))),
                    "severity": insight.get("severity"),
                    "metric": metric,
                    "value": self._round_optional(self._to_float_or_none(evidence.get("value"))),
                    "leagueAverage": self._round_optional(self._to_float_or_none(evidence.get("leagueAverage"))),
                    "zScore": self._round_optional(self._to_float_or_none(comp.get("zScore"))),
                    "percentile": self._round_optional(self._to_float_or_none(evidence.get("percentile")), digits=2),
                    "direction": comp.get("direction"),
                }
            )
        return out

    def _build_metric_comparisons_for_ml(self, comparisons: Any) -> dict[str, dict[str, Any]]:
        source = comparisons if isinstance(comparisons, dict) else {}
        out: dict[str, dict[str, Any]] = {}
        for metric_name, comp in source.items():
            if not isinstance(comp, dict):
                continue
            out[metric_name] = {
                "value": self._round_optional(self._to_float_or_none(comp.get("value"))),
                "leagueAverage": self._round_optional(self._to_float_or_none(comp.get("leagueAverage"))),
                "zScore": self._round_optional(self._to_float_or_none(comp.get("zScore"))),
                "percentile": self._round_optional(self._to_float_or_none(comp.get("percentile")), digits=2),
                "status": self._comparison_status_for_ml(comp),
                "direction": comp.get("direction"),
            }
        return out

    def _comparison_status_for_ml(self, comp: dict[str, Any]) -> str:
        status = self._as_text(comp.get("status")) or "unknown"
        if status != "normal":
            return status

        direction = self._as_text(comp.get("direction")) or ""
        percentile = self._to_float_or_none(comp.get("percentile"))
        if percentile is None:
            return status

        if direction == "higher_is_worse" and percentile >= 75.0:
            return "warning"
        if direction == "higher_is_better" and percentile <= 25.0:
            return "warning"
        return status

    @staticmethod
    def _metric_label(metric_name: str) -> str:
        labels = {
            "shotOnTargetRate": "Shot accuracy",
            "xgPerShot": "Chance quality",
            "passSuccessRate": "Pass success",
            "progressivePassSuccessRate": "Progressive pass success",
            "finalThirdPassSuccessRate": "Final third pass success",
            "lossRate": "Ball-loss rate",
            "dangerousLossRate": "Dangerous loss rate",
            "counterpressingRate": "Counterpressing rate",
            "highRecoveryRate": "High recovery rate",
            "duelSuccessRate": "Duel success",
            "aerialDuelSuccessRate": "Aerial duel success",
        }
        if metric_name in labels:
            return labels[metric_name]
        spaced = re.sub(r"(?<!^)([A-Z])", r" \1", metric_name).strip()
        return spaced[:1].upper() + spaced[1:] if spaced else metric_name

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower())
        return cleaned.strip("_")

    def _build_team_rows_from_players_stats(
        self,
        *,
        players_stats: dict[str, Any],
        match_id: int,
        home_team_name: str,
        away_team_name: str,
        home_score: int | None,
        away_score: int | None,
    ) -> list[dict[str, Any]]:
        players = players_stats.get("players")
        if not isinstance(players, list):
            raise ValueError("players_stats must contain a 'players' list.")

        home_team_id = self._resolve_team_id(home_team_name)
        away_team_id = self._resolve_team_id(away_team_name)

        rows_by_team: dict[str, dict[str, Any]] = {
            home_team_name: self._init_team_row(
                match_id=match_id,
                team_id=home_team_id,
                team_name=home_team_name,
                home_team_name=home_team_name,
                away_team_name=away_team_name,
                is_home_team=1,
                home_score=home_score,
                away_score=away_score,
            ),
            away_team_name: self._init_team_row(
                match_id=match_id,
                team_id=away_team_id,
                team_name=away_team_name,
                home_team_name=home_team_name,
                away_team_name=away_team_name,
                is_home_team=0,
                home_score=home_score,
                away_score=away_score,
            ),
        }
        team_player_counts = {home_team_name: 0, away_team_name: 0}

        for player in players:
            if not isinstance(player, dict):
                continue
            minutes = self._extract_minutes_on_field(player)
            if minutes <= 0:
                continue

            assigned_team = self._infer_team_for_player(
                player=player,
                home_team_name=home_team_name,
                away_team_name=away_team_name,
                team_player_counts=team_player_counts,
            )
            row = rows_by_team[assigned_team]
            team_player_counts[assigned_team] += 1
            row["players_count"] += 1
            row["minutes_on_field_sum"] += minutes

            total = player.get("total")
            if isinstance(total, dict):
                for metric, raw_value in total.items():
                    column = f"total_{metric}"
                    if self.total_metric_columns and column not in self.total_metric_columns:
                        continue
                    numeric = self._to_float(raw_value)
                    row[column] = self._to_float(row.get(column)) + numeric

        for row in rows_by_team.values():
            for metric in self.total_metric_columns:
                row.setdefault(metric, 0.0)
            # keep compatibility with current pipeline columns
            row.setdefault("players_assignment_explicit_team_id", 0)
            row.setdefault("players_assignment_player_intersection", 0)
            row.setdefault("players_assignment_match_balance_fallback", 0)

        return [rows_by_team[home_team_name], rows_by_team[away_team_name]]

    def _init_team_row(
        self,
        *,
        match_id: int,
        team_id: int,
        team_name: str,
        home_team_name: str,
        away_team_name: str,
        is_home_team: int,
        home_score: int | None,
        away_score: int | None,
    ) -> dict[str, Any]:
        row = {
            "match_id": match_id,
            "team_id": team_id,
            "team_name": team_name,
            "home_team_name": home_team_name,
            "away_team_name": away_team_name,
            "home_score": home_score if home_score is not None else 0,
            "away_score": away_score if away_score is not None else 0,
            "is_home_team": is_home_team,
            "players_count": 0,
            "minutes_on_field_sum": 0.0,
        }
        for metric in self.total_metric_columns:
            row[metric] = 0.0
        return row

    def _infer_team_for_player(
        self,
        *,
        player: dict[str, Any],
        home_team_name: str,
        away_team_name: str,
        team_player_counts: dict[str, int],
    ) -> str:
        player_id = self._to_int(player.get("playerId"))
        if player_id is not None:
            known_team = self.player_team_lookup.get(player_id)
            if known_team == home_team_name:
                return home_team_name
            if known_team == away_team_name:
                return away_team_name

        # fallback: keep teams balanced when player cannot be identified
        if team_player_counts[home_team_name] <= team_player_counts[away_team_name]:
            return home_team_name
        return away_team_name

    def _resolve_team_id(self, team_name: str) -> int:
        if team_name in self.team_name_to_id:
            return self.team_name_to_id[team_name]
        self.max_known_team_id += 1
        self.team_name_to_id[team_name] = self.max_known_team_id
        return self.max_known_team_id

    def _resolve_match_id(self, request_match_id: int | None, players_stats: dict[str, Any]) -> int:
        if request_match_id is not None and request_match_id not in self.existing_match_ids:
            self.existing_match_ids.add(request_match_id)
            return request_match_id

        players = players_stats.get("players")
        if isinstance(players, list):
            for player in players:
                if isinstance(player, dict):
                    candidate = self._to_int(player.get("matchId"))
                    if candidate is not None and candidate not in self.existing_match_ids:
                        self.existing_match_ids.add(candidate)
                        return candidate

        while self._synthetic_match_counter in self.existing_match_ids:
            self._synthetic_match_counter += 1
        match_id = self._synthetic_match_counter
        self.existing_match_ids.add(match_id)
        self._synthetic_match_counter += 1
        return match_id

    def _build_player_team_lookup(self, player_level_csv_path: Path) -> dict[int, str]:
        rows = self._read_csv_rows(player_level_csv_path)
        player_possible: dict[int, set[str]] = {}
        for row in rows:
            player_id = self._to_int(row.get("player_id"))
            source_file = self._as_text(row.get("source_file"))
            if player_id is None or source_file is None:
                continue
            teams = self._parse_teams_from_filename(source_file)
            if teams is None:
                continue
            pair = {teams[0], teams[1]}
            if player_id not in player_possible:
                player_possible[player_id] = set(pair)
            else:
                player_possible[player_id].intersection_update(pair)
        return {pid: next(iter(cands)) for pid, cands in player_possible.items() if len(cands) == 1}

    @staticmethod
    def _parse_teams_from_filename(file_name: str) -> tuple[str, str] | None:
        if not file_name.endswith("_players_stats.json"):
            return None
        core = file_name[: -len(".json")]
        if not core.endswith("_players_stats"):
            return None
        core = core[: -len("_players_stats")]
        id_suffix = re.search(r"_(\d+)$", core)
        if id_suffix:
            core = core[: id_suffix.start()]
        if "," not in core or " - " not in core:
            return None
        matchup, score = core.rsplit(",", 1)
        score = score.strip()
        if re.match(r"^\d+\s*-\s*\d+$", score) is None:
            return None
        home, away = matchup.split(" - ", 1)
        return home.strip(), away.strip()

    @staticmethod
    def _extract_minutes_on_field(player: dict[str, Any]) -> float:
        for candidate in (
            player.get("minutesOnField"),
            TacticalInsightsService._dict_get(player.get("total"), "minutesOnField"),
            TacticalInsightsService._dict_get(player.get("average"), "minutesOnField"),
            TacticalInsightsService._dict_get(player.get("total"), "minutesPlayed"),
            TacticalInsightsService._dict_get(player.get("average"), "minutesPlayed"),
        ):
            value = TacticalInsightsService._to_float_or_none(candidate)
            if value is not None:
                return value
        return 0.0

    @staticmethod
    def _dict_get(value: Any, key: str) -> Any:
        if isinstance(value, dict):
            return value.get(key)
        return None

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
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

    @staticmethod
    def _to_float(value: Any) -> float:
        parsed = TacticalInsightsService._to_float_or_none(value)
        return parsed if parsed is not None else 0.0

    @staticmethod
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

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return None

    @staticmethod
    def _round_optional(value: float | None, *, digits: int = 4) -> float | None:
        if value is None:
            return None
        return round(value, digits)

    @staticmethod
    def _normalize_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return " ".join(without_marks.lower().strip().split())
