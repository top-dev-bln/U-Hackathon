from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    project_root: Path
    input_dir: Path
    output_dir: Path
    input_glob: str = "*_players_stats.json"
    recursive_input_scan: bool = True
    load_report_filename: str = "load_report.json"
    player_level_csv_filename: str = "player_level_dataset.csv"
    player_level_report_filename: str = "player_level_report.json"
    team_match_csv_filename: str = "team_match_dataset.csv"
    team_match_report_filename: str = "team_match_report.json"
    team_match_heuristic_csv_filename: str = "team_match_dataset_heuristic.csv"
    team_match_strict_csv_filename: str = "team_match_dataset_strict.csv"
    team_match_heuristic_report_filename: str = "team_match_report_heuristic.json"
    team_match_strict_report_filename: str = "team_match_report_strict.json"
    team_assignment_sensitivity_report_filename: str = "team_assignment_sensitivity_report.json"
    team_match_features_csv_filename: str = "team_match_features_dataset.csv"
    team_match_features_report_filename: str = "team_match_features_report.json"
    metric_directions_filename: str = "metric_directions.json"
    league_baseline_filename: str = "league_baseline.json"
    league_distributions_filename: str = "league_distributions.json"
    u_cluj_match_comparisons_filename: str = "u_cluj_match_comparisons.json"
    u_cluj_rule_based_insights_filename: str = "u_cluj_rule_based_insights.json"
    u_cluj_tactical_weakness_report_filename: str = "u_cluj_tactical_weakness_report.json"
    anomaly_scores_csv_filename: str = "anomaly_scores.csv"
    anomaly_report_filename: str = "anomaly_report.json"
    anomaly_contamination: float = 0.1
    anomaly_random_state: int = 42
    anomaly_n_estimators: int = 300
    tactical_clusters_filename: str = "tactical_clusters.json"
    tactical_clusters_report_filename: str = "tactical_clusters_report.json"
    kmeans_n_clusters: int = 5
    kmeans_random_state: int = 42
    kmeans_n_init: int = 20
    sanity_report_filename: str = "sanity_report.json"
    max_insights_per_match: int = 6
    u_cluj_team_aliases: tuple[str, ...] = (
        "Universitatea Cluj",
        "FC Universitatea Cluj",
        "U Cluj",
    )
    team_assignment_mode: str = "strict"
    mandatory_top_level_keys: tuple[str, ...] = ("players",)
    mandatory_player_keys: tuple[str, ...] = ("matchId",)
    max_error_examples: int = 25

    def as_dict(self) -> dict[str, object]:
        return {
            "project_root": str(self.project_root),
            "input_dir": str(self.input_dir),
            "output_dir": str(self.output_dir),
            "input_glob": self.input_glob,
            "recursive_input_scan": self.recursive_input_scan,
            "load_report_filename": self.load_report_filename,
            "player_level_csv_filename": self.player_level_csv_filename,
            "player_level_report_filename": self.player_level_report_filename,
            "team_match_csv_filename": self.team_match_csv_filename,
            "team_match_report_filename": self.team_match_report_filename,
            "team_match_heuristic_csv_filename": self.team_match_heuristic_csv_filename,
            "team_match_strict_csv_filename": self.team_match_strict_csv_filename,
            "team_match_heuristic_report_filename": self.team_match_heuristic_report_filename,
            "team_match_strict_report_filename": self.team_match_strict_report_filename,
            "team_assignment_sensitivity_report_filename": self.team_assignment_sensitivity_report_filename,
            "team_match_features_csv_filename": self.team_match_features_csv_filename,
            "team_match_features_report_filename": self.team_match_features_report_filename,
            "metric_directions_filename": self.metric_directions_filename,
            "league_baseline_filename": self.league_baseline_filename,
            "league_distributions_filename": self.league_distributions_filename,
            "u_cluj_match_comparisons_filename": self.u_cluj_match_comparisons_filename,
            "u_cluj_rule_based_insights_filename": self.u_cluj_rule_based_insights_filename,
            "u_cluj_tactical_weakness_report_filename": self.u_cluj_tactical_weakness_report_filename,
            "anomaly_scores_csv_filename": self.anomaly_scores_csv_filename,
            "anomaly_report_filename": self.anomaly_report_filename,
            "anomaly_contamination": self.anomaly_contamination,
            "anomaly_random_state": self.anomaly_random_state,
            "anomaly_n_estimators": self.anomaly_n_estimators,
            "tactical_clusters_filename": self.tactical_clusters_filename,
            "tactical_clusters_report_filename": self.tactical_clusters_report_filename,
            "kmeans_n_clusters": self.kmeans_n_clusters,
            "kmeans_random_state": self.kmeans_random_state,
            "kmeans_n_init": self.kmeans_n_init,
            "sanity_report_filename": self.sanity_report_filename,
            "max_insights_per_match": self.max_insights_per_match,
            "u_cluj_team_aliases": list(self.u_cluj_team_aliases),
            "team_assignment_mode": self.team_assignment_mode,
            "mandatory_top_level_keys": list(self.mandatory_top_level_keys),
            "mandatory_player_keys": list(self.mandatory_player_keys),
            "max_error_examples": self.max_error_examples,
        }


def default_config(project_root: Path | None = None) -> PipelineConfig:
    resolved_root = project_root or Path(__file__).resolve().parents[2]
    return PipelineConfig(
        project_root=resolved_root,
        input_dir=resolved_root / "Date - meciuri",
        output_dir=resolved_root / "outputs",
    )
