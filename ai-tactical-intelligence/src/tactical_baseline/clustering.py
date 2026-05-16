from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from sklearn.cluster import KMeans

CLUSTER_FEATURES: tuple[str, ...] = (
    "passSuccessRate",
    "progressivePassSuccessRate",
    "finalThirdPassSuccessRate",
    "lossRate",
    "ownHalfLossRate",
    "dangerousLossRate",
    "shotOnTargetRate",
    "xgPerShot",
    "boxEfficiency",
    "counterpressingRate",
    "highRecoveryRate",
    "duelSuccessRate",
)


@dataclass
class TacticalClusteringResult:
    clusters_payload: dict[str, Any]
    report_payload: dict[str, Any]


def build_tactical_clusters(
    team_feature_rows: list[dict[str, Any]],
    *,
    u_cluj_aliases: list[str],
    team_assignment_mode: str,
    n_clusters: int,
    random_state: int,
    n_init: int,
) -> TacticalClusteringResult:
    normalized_aliases = {_normalize_name(alias) for alias in u_cluj_aliases}

    feature_matrix: list[list[float]] = []
    for row in team_feature_rows:
        feature_matrix.append([_to_float(row.get(feature)) for feature in CLUSTER_FEATURES])

    if len(feature_matrix) == 0:
        empty_payload = {
            "scope": {
                "team_assignment_mode": team_assignment_mode,
                "rows_used": 0,
                "feature_count": len(CLUSTER_FEATURES),
            },
            "clusters": [],
            "matches": [],
        }
        return TacticalClusteringResult(
            clusters_payload=empty_payload,
            report_payload={
                "scope": empty_payload["scope"],
                "warnings": ["No rows available for clustering."],
            },
        )

    effective_k = max(1, min(int(n_clusters), len(feature_matrix)))
    model = KMeans(
        n_clusters=effective_k,
        random_state=random_state,
        n_init=n_init,
    )
    labels = model.fit_predict(feature_matrix)

    baseline_means = _compute_baseline_means(team_feature_rows)

    cluster_to_rows: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        cluster_to_rows.setdefault(int(label), []).append(idx)

    cluster_profiles: dict[int, str] = {}
    cluster_explanations: dict[int, list[str]] = {}
    cluster_centroids_by_feature: dict[int, dict[str, float]] = {}
    cluster_counts: dict[int, int] = {}

    for cluster_id, indices in cluster_to_rows.items():
        centroid = _compute_cluster_centroid(team_feature_rows, indices)
        cluster_centroids_by_feature[cluster_id] = centroid
        cluster_counts[cluster_id] = len(indices)
        profile, explanation = _label_cluster(centroid, baseline_means)
        cluster_profiles[cluster_id] = profile
        cluster_explanations[cluster_id] = explanation

    match_rows: list[dict[str, Any]] = []
    u_cluj_distribution: dict[int, int] = {}
    for idx, row in enumerate(team_feature_rows):
        cluster_id = int(labels[idx])
        team_name = _as_text(row.get("team_name")) or ""
        is_u_cluj = int(_normalize_name(team_name) in normalized_aliases)
        if is_u_cluj:
            u_cluj_distribution[cluster_id] = u_cluj_distribution.get(cluster_id, 0) + 1

        match_rows.append(
            {
                "matchId": _to_int(row.get("match_id")),
                "teamId": _to_int(row.get("team_id")),
                "teamName": team_name,
                "clusterId": cluster_id,
                "tacticalProfile": cluster_profiles[cluster_id],
                "clusterExplanation": cluster_explanations[cluster_id],
                "isUCluj": is_u_cluj,
            }
        )

    cluster_rows = []
    for cluster_id in sorted(cluster_to_rows):
        cluster_rows.append(
            {
                "clusterId": cluster_id,
                "tacticalProfile": cluster_profiles[cluster_id],
                "count": cluster_counts[cluster_id],
                "clusterExplanation": cluster_explanations[cluster_id],
                "centroidMetrics": cluster_centroids_by_feature[cluster_id],
            }
        )

    clusters_payload = {
        "scope": {
            "team_assignment_mode": team_assignment_mode,
            "rows_used": len(team_feature_rows),
            "feature_count": len(CLUSTER_FEATURES),
            "k": effective_k,
        },
        "clusters": cluster_rows,
        "matches": match_rows,
    }

    report_payload = {
        "scope": clusters_payload["scope"],
        "model": {
            "name": "KMeans",
            "k": effective_k,
            "random_state": random_state,
            "n_init": n_init,
            "features": list(CLUSTER_FEATURES),
            "inertia": float(model.inertia_),
        },
        "cluster_sizes": [
            {"clusterId": cid, "count": cluster_counts[cid], "tacticalProfile": cluster_profiles[cid]}
            for cid in sorted(cluster_counts)
        ],
        "u_cluj_cluster_distribution": [
            {"clusterId": cid, "count": count, "tacticalProfile": cluster_profiles[cid]}
            for cid, count in sorted(u_cluj_distribution.items(), key=lambda item: item[0])
        ],
    }

    return TacticalClusteringResult(
        clusters_payload=clusters_payload,
        report_payload=report_payload,
    )


def _compute_baseline_means(rows: list[dict[str, Any]]) -> dict[str, float]:
    sums = {feature: 0.0 for feature in CLUSTER_FEATURES}
    for row in rows:
        for feature in CLUSTER_FEATURES:
            sums[feature] += _to_float(row.get(feature))
    count = len(rows)
    if count == 0:
        return {feature: 0.0 for feature in CLUSTER_FEATURES}
    return {feature: sums[feature] / count for feature in CLUSTER_FEATURES}


def _compute_cluster_centroid(rows: list[dict[str, Any]], indices: list[int]) -> dict[str, float]:
    if not indices:
        return {feature: 0.0 for feature in CLUSTER_FEATURES}
    sums = {feature: 0.0 for feature in CLUSTER_FEATURES}
    for idx in indices:
        row = rows[idx]
        for feature in CLUSTER_FEATURES:
            sums[feature] += _to_float(row.get(feature))
    size = len(indices)
    return {feature: sums[feature] / size for feature in CLUSTER_FEATURES}


def _label_cluster(centroid: dict[str, float], baseline: dict[str, float]) -> tuple[str, list[str]]:
    loss_delta = centroid["lossRate"] - baseline["lossRate"]
    progression_delta = centroid["progressivePassSuccessRate"] - baseline["progressivePassSuccessRate"]
    pressing_delta = centroid["counterpressingRate"] - baseline["counterpressingRate"]
    final_third_delta = centroid["xgPerShot"] - baseline["xgPerShot"]
    pass_success_delta = centroid["passSuccessRate"] - baseline["passSuccessRate"]

    explanation: list[str] = []
    if loss_delta > 0.015:
        explanation.append("higher than average ball losses")
    elif loss_delta < -0.015:
        explanation.append("lower than average ball losses")

    if progression_delta > 0.03:
        explanation.append("higher than average progressive passing success")
    elif progression_delta < -0.03:
        explanation.append("lower than average progressive passing success")

    if pressing_delta > 0.04:
        explanation.append("stronger than average counterpressing")
    elif pressing_delta < -0.04:
        explanation.append("weaker than average counterpressing")

    if final_third_delta > 0.015:
        explanation.append("higher than average chance quality per shot")
    elif final_third_delta < -0.015:
        explanation.append("lower than average chance quality per shot")

    if pass_success_delta < -0.06:
        explanation.append("lower than average overall pass success")

    if loss_delta > 0.015 and progression_delta < -0.03:
        if final_third_delta > 0.015:
            profile = "high_loss_low_progression_with_chance_quality"
        else:
            profile = "high_loss_low_control"
    elif pressing_delta > 0.04 and loss_delta <= 0.015:
        profile = "strong_pressing_compact"
    elif final_third_delta < -0.015 and progression_delta >= -0.03:
        profile = "low_chance_creation"
    elif progression_delta > 0.03 and loss_delta < 0:
        profile = "balanced_control"
    else:
        profile = "mixed_profile"

    if not explanation:
        explanation = ["balanced around league baseline values"]

    return profile, explanation


def _normalize_name(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(without_marks.lower().strip().split())


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


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


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
