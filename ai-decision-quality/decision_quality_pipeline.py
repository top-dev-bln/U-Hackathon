from __future__ import annotations

import argparse
import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ACTION_TYPES: Tuple[str, str, str] = ("pass", "shot", "carry")
SUPPORTED_MODELS: Tuple[str, str, str] = ("auto", "random_forest", "mlp")


def parse_bool(series: pd.Series) -> pd.Series:
    lowered = series.fillna("").astype(str).str.strip().str.lower()
    return lowered.isin({"1", "true", "yes"})


def load_actions(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df[df["event_primary"].isin(ACTION_TYPES)].copy()

    numeric_cols = [
        "event_id",
        "minute",
        "second",
        "x",
        "y",
        "pass_end_x",
        "pass_end_y",
        "pass_length",
        "pass_angle",
        "shot_xg",
        "carry_end_x",
        "carry_end_y",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["event_id"] = df["event_id"].fillna(0).astype(int)
    df["minute"] = df["minute"].fillna(0).astype(int)
    df["second"] = df["second"].fillna(0).astype(int)
    df["shot_is_goal_bool"] = parse_bool(df.get("shot_is_goal", pd.Series(index=df.index, dtype=object)))

    df = df.sort_values(
        by=["match_id", "minute", "second", "event_id"],
        kind="mergesort",
    ).reset_index(drop=True)
    df["absolute_second"] = df["minute"] * 60 + df["second"]
    return df


def add_context_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()

    data["x"] = data["x"].fillna(0.0)
    data["y"] = data["y"].fillna(0.0)
    data["position"] = data["position"].fillna("UNK")
    data["period"] = data["period"].fillna("UNK")
    data["team_id"] = data["team_id"].astype(str)
    data["player_id"] = data["player_id"].astype(str)
    data["team_name"] = data["team_name"].fillna("UNK")
    data["possession_flank"] = data["possession_flank"].fillna("unknown")
    data["is_u_cluj"] = (data["team_name"] == "FC Universitatea Cluj").astype(int)

    data["distance_to_goal"] = np.sqrt((100.0 - data["x"]) ** 2 + (50.0 - data["y"]) ** 2)
    data["angle_to_goal"] = np.degrees(np.arctan2(np.abs(50.0 - data["y"]), (100.0 - data["x"]) + 1e-6))
    data["zone_x"] = np.clip((data["x"] // 10).astype(int), 0, 9)
    data["zone_y"] = np.clip((data["y"] // 10).astype(int), 0, 9)
    data["is_final_third"] = (data["x"] >= 66.7).astype(int)
    data["is_box_entry_zone"] = ((data["x"] >= 83.0) & (data["y"].between(21.0, 79.0))).astype(int)

    group_keys = ["match_id", "team_id"]
    prev_event = data.groupby(group_keys)["event_primary"].shift(1)
    prev_position = data.groupby(group_keys)["position"].shift(1)
    prev_x = data.groupby(group_keys)["x"].shift(1)
    prev_y = data.groupby(group_keys)["y"].shift(1)
    prev_abs = data.groupby(group_keys)["absolute_second"].shift(1)
    prev_player = data.groupby(group_keys)["player_id"].shift(1)
    prev_possession = data.groupby(group_keys)["possession_id"].shift(1)

    data["previous_event_primary"] = prev_event.fillna("none")
    data["previous_position"] = prev_position.fillna("none")
    data["previous_x"] = prev_x.fillna(data["x"])
    data["previous_y"] = prev_y.fillna(data["y"])
    data["seconds_since_previous_action"] = (data["absolute_second"] - prev_abs).fillna(0).clip(lower=0)
    data["same_player_as_previous"] = (data["player_id"] == prev_player).fillna(False).astype(int)
    data["same_possession_as_previous"] = (data["possession_id"] == prev_possession).fillna(False).astype(int)
    return data


def create_label(df: pd.DataFrame, window_seconds: int = 10) -> pd.Series:
    labels = np.zeros(len(df), dtype=np.int8)

    for _, idx in df.groupby(["match_id", "team_id"]).groups.items():
        idx_array = np.fromiter(idx, dtype=np.int64)
        sub = df.loc[idx_array]

        times = sub["absolute_second"].to_numpy()
        has_shot_or_goal = (sub["event_primary"] == "shot") | sub["shot_is_goal_bool"]
        shot_times = times[has_shot_or_goal.to_numpy()]
        if shot_times.size == 0:
            continue

        left = np.searchsorted(shot_times, times, side="right")
        right = np.searchsorted(shot_times, times + window_seconds, side="right")
        labels[idx_array] = (right > left).astype(np.int8)

    return pd.Series(labels, index=df.index, name="label")


def build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], List[str]]:
    feature_df = pd.DataFrame(index=df.index)

    categorical_cols = [
        "event_primary",
        "position",
        "period",
        "team_id",
        "possession_flank",
        "previous_event_primary",
        "previous_position",
    ]
    numeric_cols = [
        "minute",
        "second",
        "x",
        "y",
        "distance_to_goal",
        "angle_to_goal",
        "zone_x",
        "zone_y",
        "is_final_third",
        "is_box_entry_zone",
        "is_u_cluj",
        "previous_x",
        "previous_y",
        "seconds_since_previous_action",
        "same_player_as_previous",
        "same_possession_as_previous",
    ]

    for col in categorical_cols:
        feature_df[col] = df[col].fillna("unknown").astype(str)
    for col in numeric_cols:
        feature_df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return feature_df, categorical_cols, numeric_cols


def get_pipeline(
    model_name: str,
    categorical_cols: Sequence[str],
    numeric_cols: Sequence[str],
    random_state: int,
) -> Pipeline:
    if model_name == "random_forest":
        preprocessor = ColumnTransformer(
            transformers=[
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=True), list(categorical_cols)),
                ("num", "passthrough", list(numeric_cols)),
            ],
            remainder="drop",
        )
        estimator = RandomForestClassifier(
            n_estimators=700,
            max_depth=14,
            min_samples_leaf=4,
            min_samples_split=12,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=random_state,
        )
        return Pipeline([("preprocess", preprocessor), ("model", estimator)])

    if model_name == "mlp":
        preprocessor = ColumnTransformer(
            transformers=[
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(categorical_cols)),
                ("num", StandardScaler(), list(numeric_cols)),
            ],
            remainder="drop",
        )
        estimator = MLPClassifier(
            hidden_layer_sizes=(256, 128, 64),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            learning_rate_init=3e-4,
            batch_size=128,
            max_iter=350,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=20,
            random_state=random_state,
        )
        return Pipeline([("preprocess", preprocessor), ("model", estimator)])

    raise ValueError(f"Unsupported model name: {model_name}")


def _positive_probability(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    proba = model.predict_proba(X)
    classes = np.asarray(getattr(model, "classes_", [0, 1]))
    if proba.ndim == 1:
        return proba
    if 1 in classes:
        pos_idx = int(np.where(classes == 1)[0][0])
    else:
        pos_idx = proba.shape[1] - 1
    return proba[:, pos_idx]


def _safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> Optional[float]:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_prob))


@dataclass
class CandidateSummary:
    model: str
    folds: int
    mean_roc_auc: Optional[float]
    std_roc_auc: Optional[float]
    mean_average_precision: Optional[float]
    mean_brier: Optional[float]


def evaluate_candidate(
    base_pipeline: Pipeline,
    model_name: str,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    n_splits: int,
) -> CandidateSummary:
    unique_groups = groups.nunique()
    effective_splits = min(n_splits, unique_groups)
    if effective_splits < 2:
        return CandidateSummary(
            model=model_name,
            folds=0,
            mean_roc_auc=None,
            std_roc_auc=None,
            mean_average_precision=None,
            mean_brier=None,
        )

    gkf = GroupKFold(n_splits=effective_splits)
    auc_scores: List[float] = []
    ap_scores: List[float] = []
    brier_scores: List[float] = []

    for train_idx, valid_idx in gkf.split(X, y, groups):
        X_train = X.iloc[train_idx]
        y_train = y.iloc[train_idx]
        X_valid = X.iloc[valid_idx]
        y_valid = y.iloc[valid_idx]

        model = clone(base_pipeline)
        model.fit(X_train, y_train)
        y_prob = _positive_probability(model, X_valid)

        fold_auc = _safe_auc(y_valid.to_numpy(), y_prob)
        if fold_auc is not None:
            auc_scores.append(fold_auc)
        ap_scores.append(float(average_precision_score(y_valid, y_prob)))
        brier_scores.append(float(brier_score_loss(y_valid, y_prob)))

    return CandidateSummary(
        model=model_name,
        folds=effective_splits,
        mean_roc_auc=float(np.mean(auc_scores)) if auc_scores else None,
        std_roc_auc=float(np.std(auc_scores)) if auc_scores else None,
        mean_average_precision=float(np.mean(ap_scores)) if ap_scores else None,
        mean_brier=float(np.mean(brier_scores)) if brier_scores else None,
    )


def select_model(
    model_choice: str,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    categorical_cols: Sequence[str],
    numeric_cols: Sequence[str],
    cv_splits: int,
    random_state: int,
) -> Tuple[str, Pipeline, List[CandidateSummary]]:
    candidates = ["random_forest", "mlp"] if model_choice == "auto" else [model_choice]

    summaries: List[CandidateSummary] = []
    pipelines: Dict[str, Pipeline] = {}

    for candidate in candidates:
        pipe = get_pipeline(candidate, categorical_cols, numeric_cols, random_state=random_state)
        pipelines[candidate] = pipe
        summary = evaluate_candidate(
            base_pipeline=pipe,
            model_name=candidate,
            X=X,
            y=y,
            groups=groups,
            n_splits=cv_splits,
        )
        summaries.append(summary)

    if model_choice != "auto":
        selected_name = model_choice
        selected_pipe = pipelines[selected_name]
        return selected_name, selected_pipe, summaries

    def score_key(item: CandidateSummary) -> Tuple[float, float, float]:
        auc = item.mean_roc_auc if item.mean_roc_auc is not None else -1.0
        ap = item.mean_average_precision if item.mean_average_precision is not None else -1.0
        brier = -(item.mean_brier if item.mean_brier is not None else 1.0)
        return (auc, ap, brier)

    best = max(summaries, key=score_key)
    return best.model, pipelines[best.model], summaries


def summarize_events(
    base_df: pd.DataFrame,
    feature_df: pd.DataFrame,
    model: Pipeline,
    low_score_quantile: float,
    min_improvement: float,
) -> Tuple[pd.DataFrame, float]:
    events = base_df.copy()
    decision_probs = {}

    for action in ACTION_TYPES:
        variant_X = feature_df.copy()
        variant_X["event_primary"] = action
        decision_probs[action] = _positive_probability(model, variant_X)

    events["pred_pass"] = decision_probs["pass"]
    events["pred_shot"] = decision_probs["shot"]
    events["pred_carry"] = decision_probs["carry"]

    actions = events["event_primary"].to_numpy()
    actual = np.zeros(len(events), dtype=float)
    for action in ACTION_TYPES:
        mask = actions == action
        actual[mask] = decision_probs[action][mask]
    events["decisionValue"] = actual

    pred_matrix = events[["pred_pass", "pred_shot", "pred_carry"]].to_numpy()
    best_idx = pred_matrix.argmax(axis=1)
    events["bestDecisionType"] = np.array(ACTION_TYPES, dtype=object)[best_idx]
    events["bestDecisionValue"] = pred_matrix[np.arange(len(events)), best_idx]
    events["potentialGain"] = events["bestDecisionValue"] - events["decisionValue"]
    events["decisionValuePercentile"] = events["decisionValue"].rank(method="average", pct=True)

    low_score_threshold = float(events["decisionValue"].quantile(low_score_quantile))
    events["isLowDecision"] = events["decisionValue"] <= low_score_threshold

    suggest_mask = (
        events["isLowDecision"]
        & (events["bestDecisionType"] != events["event_primary"])
        & (events["potentialGain"] >= min_improvement)
    )
    events["suggestedAlternative"] = np.where(suggest_mask, events["bestDecisionType"], None)

    export_cols = [
        "event_id",
        "match_id",
        "team_id",
        "team_name",
        "player_id",
        "player_name",
        "position",
        "minute",
        "second",
        "event_primary",
        "x",
        "y",
        "label",
        "decisionValue",
        "decisionValuePercentile",
        "pred_pass",
        "pred_shot",
        "pred_carry",
        "bestDecisionType",
        "bestDecisionValue",
        "potentialGain",
        "isLowDecision",
        "suggestedAlternative",
    ]
    return events[export_cols].rename(columns={"event_primary": "decision"}), low_score_threshold


def _most_common(series: pd.Series) -> Optional[str]:
    s = series.dropna()
    if s.empty:
        return None
    return str(s.value_counts().idxmax())


def summarize_players(events: pd.DataFrame, min_player_actions: int) -> pd.DataFrame:
    players = (
        events.groupby(["player_id", "player_name"], as_index=False)
        .agg(
            decisionScore=("decisionValue", "mean"),
            actionsAnalyzed=("event_id", "count"),
            lowScoreActions=("isLowDecision", "sum"),
            suggestedActions=("suggestedAlternative", lambda s: int(s.notna().sum())),
        )
        .sort_values("decisionScore", ascending=False)
        .reset_index(drop=True)
    )

    gain_source = events.copy()
    gain_source["suggestedGain"] = np.where(
        gain_source["suggestedAlternative"].notna(),
        gain_source["potentialGain"],
        np.nan,
    )
    gain_df = (
        gain_source.groupby(["player_id", "player_name"], as_index=False)["suggestedGain"]
        .mean()
        .rename(columns={"suggestedGain": "avgPotentialGainOnSuggestions"})
    )
    players = players.merge(gain_df, on=["player_id", "player_name"], how="left")
    players["avgPotentialGainOnSuggestions"] = players["avgPotentialGainOnSuggestions"].fillna(0.0)

    rec = (
        events[events["suggestedAlternative"].notna()]
        .groupby(["player_id", "player_name"], as_index=False)["suggestedAlternative"]
        .agg(_most_common)
        .rename(columns={"suggestedAlternative": "recommendedDecisionTypeWhenLow"})
    )
    players = players.merge(rec, on=["player_id", "player_name"], how="left")

    decision_type_mean = (
        events.groupby(["player_id", "player_name", "decision"], as_index=False)["decisionValue"]
        .mean()
        .rename(columns={"decisionValue": "meanDecisionValue"})
    )
    best_type = (
        decision_type_mean.sort_values("meanDecisionValue", ascending=False)
        .groupby(["player_id", "player_name"], as_index=False)
        .first()
        .rename(columns={"decision": "bestDecisionType"})
        .drop(columns=["meanDecisionValue"])
    )
    weak_type = (
        decision_type_mean.sort_values("meanDecisionValue", ascending=True)
        .groupby(["player_id", "player_name"], as_index=False)
        .first()
        .rename(columns={"decision": "weakDecisionType"})
        .drop(columns=["meanDecisionValue"])
    )
    players = players.merge(best_type, on=["player_id", "player_name"], how="left")
    players = players.merge(weak_type, on=["player_id", "player_name"], how="left")

    low_player_threshold = float(players["decisionScore"].quantile(0.25))
    players["decisionScorePercentile"] = players["decisionScore"].rank(method="average", pct=True)
    players["needsDecisionSupport"] = (
        (players["decisionScore"] <= low_player_threshold)
        & (players["actionsAnalyzed"] >= min_player_actions)
    )
    return players


def write_outputs(
    output_dir: Path,
    events: pd.DataFrame,
    players: pd.DataFrame,
    report: Dict,
    trained_model: Pipeline,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    events_csv = output_dir / "u_cluj_decision_quality_event_predictions.csv"
    events_json = output_dir / "u_cluj_decision_quality_event_predictions.json"
    players_csv = output_dir / "u_cluj_decision_quality_player_scores.csv"
    players_json = output_dir / "u_cluj_decision_quality_player_scores.json"
    report_json = output_dir / "u_cluj_decision_quality_model_report.json"
    model_bin = output_dir / "u_cluj_decision_quality_model.joblib"

    events.to_csv(events_csv, index=False)
    players.to_csv(players_csv, index=False)
    with events_json.open("w", encoding="utf-8") as f:
        json.dump(events.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
    with players_json.open("w", encoding="utf-8") as f:
        json.dump(players.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
    with report_json.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    joblib.dump(trained_model, model_bin)


def run_pipeline(
    csv_input: Path,
    output_dir: Path,
    model_choice: str,
    window_seconds: int,
    low_score_quantile: float,
    min_improvement: float,
    cv_splits: int,
    random_state: int,
    min_player_actions: int,
) -> Dict:
    raw = load_actions(csv_input)
    enriched = add_context_features(raw)
    enriched["label"] = create_label(enriched, window_seconds=window_seconds)

    X, categorical_cols, numeric_cols = build_feature_matrix(enriched)
    y = enriched["label"].astype(int)
    groups = enriched["match_id"].astype(str)

    selected_name, selected_pipeline, summaries = select_model(
        model_choice=model_choice,
        X=X,
        y=y,
        groups=groups,
        categorical_cols=categorical_cols,
        numeric_cols=numeric_cols,
        cv_splits=cv_splits,
        random_state=random_state,
    )

    trained_model = clone(selected_pipeline)
    trained_model.fit(X, y)

    events, low_score_threshold = summarize_events(
        base_df=enriched,
        feature_df=X,
        model=trained_model,
        low_score_quantile=low_score_quantile,
        min_improvement=min_improvement,
    )
    players = summarize_players(events, min_player_actions=min_player_actions)

    report = {
        "selectedModel": selected_name,
        "candidateEvaluation": [asdict(s) for s in summaries],
        "dataset": {
            "actionsAnalyzed": int(len(events)),
            "playersAnalyzed": int(len(players)),
            "positiveLabelCount": int(y.sum()),
            "positiveLabelRate": float(y.mean()),
            "matches": int(groups.nunique()),
        },
        "thresholds": {
            "lowScoreQuantile": float(low_score_quantile),
            "lowScoreDecisionValueThreshold": float(low_score_threshold),
            "minImprovementForSuggestion": float(min_improvement),
            "windowSeconds": int(window_seconds),
        },
        "featureColumns": {
            "categorical": list(categorical_cols),
            "numeric": list(numeric_cols),
        },
    }

    write_outputs(
        output_dir=output_dir,
        events=events,
        players=players,
        report=report,
        trained_model=trained_model,
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decision Quality ML pipeline with action alternatives.")
    parser.add_argument("--csv-input", type=Path, default=Path("u_cluj_10_matches_flat_ml_dataset.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--model", type=str, default="auto", choices=SUPPORTED_MODELS)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--low-score-quantile", type=float, default=0.25)
    parser.add_argument("--min-improvement", type=float, default=0.02)
    parser.add_argument("--cv-splits", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--min-player-actions", type=int, default=15)
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.window_seconds <= 0:
        raise ValueError("window-seconds must be > 0.")
    if not (0.0 < args.low_score_quantile < 1.0):
        raise ValueError("low-score-quantile must be in (0, 1).")
    if args.min_improvement < 0:
        raise ValueError("min-improvement must be >= 0.")
    if args.cv_splits < 2:
        raise ValueError("cv-splits must be >= 2.")
    if args.min_player_actions <= 0:
        raise ValueError("min-player-actions must be > 0.")


def main() -> None:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    parser = build_parser()
    args = parser.parse_args()
    validate_args(args)

    report = run_pipeline(
        csv_input=args.csv_input,
        output_dir=args.output_dir,
        model_choice=args.model,
        window_seconds=args.window_seconds,
        low_score_quantile=args.low_score_quantile,
        min_improvement=args.min_improvement,
        cv_splits=args.cv_splits,
        random_state=args.random_state,
        min_player_actions=args.min_player_actions,
    )

    dataset = report["dataset"]
    thresholds = report["thresholds"]
    print("Decision Quality ML pipeline complete")
    print(f"selected_model={report['selectedModel']}")
    print(f"actions_analyzed={dataset['actionsAnalyzed']}")
    print(f"players_analyzed={dataset['playersAnalyzed']}")
    print(f"label_rate={dataset['positiveLabelRate']:.4f}")
    print(f"low_score_threshold={thresholds['lowScoreDecisionValueThreshold']:.4f}")


if __name__ == "__main__":
    main()
