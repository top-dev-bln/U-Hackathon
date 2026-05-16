from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path


TACTICAL_CATEGORIES = [
    "build_up",
    "ball_loss",
    "progression",
    "final_third",
    "duels",
    "pressing",
]

METRICS_BY_CATEGORY = {
    "build_up": ["progressivePassSuccessRate", "finalThirdPassSuccessRate", "passSuccessRate"],
    "ball_loss": ["lossRate", "ownHalfLossRate", "dangerousLossRate"],
    "progression": ["forwardPassSuccessRate", "progressivePassSuccessRate"],
    "final_third": ["xgPerShot", "boxEfficiency", "shotOnTargetRate"],
    "duels": ["duelSuccessRate", "aerialDuelSuccessRate", "defensiveDuelSuccessRate"],
    "pressing": ["highRecoveryRate", "counterpressingRate"],
}

PLAYER_POOL = [
    "A. Gorcea",
    "A. Miron",
    "I. Stoica",
    "M. Thiam",
    "D. Nistor",
    "O. Bic",
    "D. Popa",
    "L. Cristea",
    "A. Chipciu",
    "D. Oancea",
    "V. Gheorghe",
]

TEAM_NAMES = [
    "FC Universitatea Cluj",
    "FC Hermannstadt",
    "Sepsi OSK",
    "Petrolul Ploiesti",
    "Farul Constanta",
    "Rapid Bucuresti",
    "CFR Cluj",
    "FCSB",
    "U Craiova 1948",
    "UTA Arad",
]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def severity_band(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def make_baseline_model(rng: random.Random, base_risk: float) -> dict:
    risk_level = "medium"
    if base_risk >= 0.72:
        risk_level = "high"
    elif base_risk <= 0.35:
        risk_level = "low"
    elif base_risk >= 0.55:
        risk_level = "medium-high"

    return {
        "overallWeaknessScore": round(clamp01(base_risk + rng.uniform(-0.08, 0.08)), 4),
        "riskLevel": risk_level,
        "tacticalProfile": rng.choice(
            [
                "high_loss_low_control",
                "direct_vertical_risk",
                "passive_pressing",
                "stable_progression",
            ]
        ),
        "clusterId": rng.randint(1, 4),
        "anomalyScore": round(clamp01(base_risk + rng.uniform(-0.12, 0.12)), 4),
        "isAnomalous": base_risk > 0.7,
    }


def make_input1(
    rng: random.Random,
    sample_match_id: int,
    team_id: int,
    team_name: str,
    category_truth: dict[str, float],
) -> dict:
    weakness_signals = []
    metric_comparisons = {}

    for category in TACTICAL_CATEGORIES:
        score = category_truth[category]
        metric = rng.choice(METRICS_BY_CATEGORY[category])
        weakness_signals.append(
            {
                "signalId": f"{category}.{metric}",
                "category": category,
                "severityScore": round(clamp01(score + rng.uniform(-0.07, 0.07)), 4),
                "severity": severity_band(score),
                "metric": metric,
                "value": round(rng.uniform(0.05, 0.85), 4),
                "leagueAverage": round(rng.uniform(0.12, 0.78), 4),
                "zScore": round(rng.uniform(-2.8, 2.8), 4),
                "percentile": round(rng.uniform(1.0, 99.0), 2),
                "direction": "higher_is_worse" if category in {"ball_loss"} else "higher_is_better",
            }
        )

    for category, metrics in METRICS_BY_CATEGORY.items():
        for metric in metrics[:2]:
            metric_score = clamp01(category_truth[category] + rng.uniform(-0.15, 0.15))
            metric_comparisons[metric] = {
                "value": round(rng.uniform(0.05, 0.88), 4),
                "leagueAverage": round(rng.uniform(0.1, 0.8), 4),
                "zScore": round(rng.uniform(-3.0, 3.0), 4),
                "percentile": round(rng.uniform(1.0, 99.0), 2),
                "status": severity_band(metric_score),
                "direction": "higher_is_worse" if category in {"ball_loss"} else "higher_is_better",
            }

    overall_risk = sum(category_truth.values()) / len(category_truth)
    return {
        "matchId": sample_match_id,
        "teamId": team_id,
        "teamName": team_name,
        "baselineModel": make_baseline_model(rng, overall_risk),
        "weaknessSignals": weakness_signals,
        "metricComparisons": metric_comparisons,
    }


def _decision_from_category(rng: random.Random, category: str) -> str:
    if category == "build_up":
        return "pass"
    if category == "progression":
        return "carry"
    if category == "final_third":
        return rng.choice(["shot", "pass"])
    return rng.choice(["pass", "carry", "shot"])


def _generate_needs_support(
    rng: random.Random, category_truth: dict[str, float], count: int
) -> list[dict]:
    signals = []
    ranked_categories = sorted(category_truth.items(), key=lambda kv: kv[1], reverse=True)
    weak_mapping = {
        "build_up": "pass",
        "progression": "carry",
        "final_third": "shot",
        "ball_loss": "pass",
        "pressing": "carry",
        "duels": "shot",
    }
    chosen_players = rng.sample(PLAYER_POOL, k=min(count, len(PLAYER_POOL)))
    for idx, player_name in enumerate(chosen_players):
        focus_category = ranked_categories[idx % len(ranked_categories)][0]
        severity = category_truth[focus_category]
        decision_score = clamp01(0.3 - severity * 0.2 + rng.uniform(-0.03, 0.05))
        actions = rng.randint(14, 42)
        low_actions = min(actions, int(actions * clamp01(0.3 + severity * 0.5)))
        signals.append(
            {
                "player_id": f"{1000 + PLAYER_POOL.index(player_name)}",
                "player_name": player_name,
                "decisionScore": round(decision_score, 4),
                "actionsAnalyzed": actions,
                "lowScoreActions": low_actions,
                "suggestedActions": rng.randint(0, 4),
                "avgPotentialGainOnSuggestions": round(rng.uniform(0.01, 0.07), 4),
                "recommendedDecisionTypeWhenLow": rng.choice(["pass", "carry", "shot", None]),
                "bestDecisionType": rng.choice(["pass", "carry", "shot"]),
                "weakDecisionType": weak_mapping[focus_category],
                "needsDecisionSupport": True,
            }
        )
    return signals


def _generate_improvable_phases(
    rng: random.Random, category_truth: dict[str, float], total: int
) -> list[dict]:
    phases = []
    sorted_categories = sorted(category_truth.items(), key=lambda kv: kv[1], reverse=True)
    for i in range(total):
        category = sorted_categories[i % len(sorted_categories)][0]
        decision = _decision_from_category(rng, category)
        player_name = rng.choice(PLAYER_POOL)
        decision_value = clamp01(0.09 + rng.uniform(0.0, 0.12) + (1 - category_truth[category]) * 0.07)
        potential_gain = clamp01(0.01 + category_truth[category] * 0.07 + rng.uniform(0.0, 0.02))
        event_id = 880000000 + rng.randint(100, 99999)
        phases.append(
            {
                "event_id": event_id,
                "minute": rng.randint(1, 94),
                "second": rng.randint(0, 59),
                "player_name": player_name,
                "team_name": "TeamScope",
                "decision": decision,
                "decisionValue": round(decision_value, 4),
                "bestDecisionType": rng.choice(["pass", "carry", "shot"]),
                "bestDecisionValue": round(clamp01(decision_value + potential_gain), 4),
                "potentialGain": round(potential_gain, 4),
                "suggestedAlternative": rng.choice(["pass", "carry", "shot"]),
                "label": rng.choice([0, 1]),
                "actualShotOnTarget": rng.choice([True, False]),
                "actualGoal": rng.choice([True, False, False, False]),
            }
        )
    return phases


def _generate_missed_opportunities(rng: random.Random, total: int) -> list[dict]:
    rows = []
    for _ in range(total):
        decision = rng.choice(["pass", "carry", "shot"])
        decision_value = round(rng.uniform(0.2, 0.38), 4)
        best_value = round(clamp01(decision_value + rng.uniform(0.02, 0.06)), 4)
        rows.append(
            {
                "event_id": 880000000 + rng.randint(100, 99999),
                "minute": rng.randint(1, 94),
                "second": rng.randint(0, 59),
                "player_name": rng.choice(PLAYER_POOL),
                "team_name": "TeamScope",
                "decision": decision,
                "decisionValue": decision_value,
                "bestDecisionType": rng.choice(["pass", "carry", "shot"]),
                "bestDecisionValue": best_value,
                "potentialGain": round(best_value - decision_value, 4),
                "suggestedAlternative": None,
                "label": rng.choice([0, 1]),
                "actualShotOnTarget": rng.choice([True, False]),
                "actualGoal": rng.choice([True, False, False]),
            }
        )
    return rows


def _generate_team_decision_stats(rng: random.Random) -> list[dict]:
    rows = []
    for decision in ["pass", "carry", "shot"]:
        actions = rng.randint(25, 280) if decision == "pass" else rng.randint(20, 90)
        avg_value = round(rng.uniform(0.16, 0.29), 4)
        low = rng.randint(5, max(6, int(actions * 0.38)))
        rows.append(
            {
                "decision": decision,
                "actions": actions,
                "avgDecisionValue": avg_value,
                "avgPotentialGain": round(rng.uniform(0.003, 0.025), 4),
                "lowDecisionPhases": low,
            }
        )
    return rows


def make_input2(
    rng: random.Random,
    sample_match_id: int,
    team_id: int,
    team_name: str,
    category_truth: dict[str, float],
    match_dt: date,
) -> dict:
    actions_analyzed = rng.randint(260, 430)
    avg_decision_value = round(rng.uniform(0.17, 0.27), 6)
    low_decision_phases = rng.randint(45, 130)
    phases_with_alternative = rng.randint(8, 28)
    missed_opportunities_count = rng.randint(3, 10)

    needs_support_count = rng.randint(3, 6)
    improvable_count = rng.randint(8, 18)

    needs_support = _generate_needs_support(rng, category_truth, needs_support_count)
    improvable = _generate_improvable_phases(rng, category_truth, improvable_count)
    missed = _generate_missed_opportunities(rng, missed_opportunities_count)
    by_type = _generate_team_decision_stats(rng)

    timeline = []
    for minute_bucket in ["0-14", "15-29", "30-44", "45-59", "60-74", "75-89", "90-104"]:
        actions = rng.randint(20, 70)
        timeline.append(
            {
                "actions": actions,
                "avgDecisionValue": round(rng.uniform(0.16, 0.28), 4),
                "lowDecisionPhases": rng.randint(4, 18),
                "phasesWithAlternative": rng.randint(0, 6),
                "minuteBucket": minute_bucket,
            }
        )

    return {
        "match": {
            "matchId": sample_match_id,
            "label": f"{team_name} vs {rng.choice([t for t in TEAM_NAMES if t != team_name])}",
            "date": f"{match_dt.isoformat()}T17:30:00+03:00",
            "status": "played",
            "venue": rng.choice(["Cluj Arena", "Arena Nationala", "Rapid-Giulesti", "Stadion Central"]),
            "teams": [
                {"teamId": team_id, "teamName": team_name, "formation": rng.choice(["4-2-3-1", "4-3-3", "3-4-3"])},
                {"teamId": 9000 + rng.randint(2, 30), "teamName": rng.choice(TEAM_NAMES), "formation": rng.choice(["4-2-3-1", "4-3-3", "3-5-2"])},
            ],
            "teamScope": team_name,
        },
        "summary": {
            "actionsAnalyzed": actions_analyzed,
            "playersAnalyzed": 11,
            "averageDecisionValue": avg_decision_value,
            "lowDecisionPhases": low_decision_phases,
            "phasesWithAlternative": phases_with_alternative,
            "missedShotOrGoalOpportunities": missed_opportunities_count,
            "lowScoreThresholdUsed": round(rng.uniform(0.14, 0.18), 6),
        },
        "players": {
            "needsSupport": needs_support,
        },
        "phases": {
            "improvablePhases": improvable,
            "missedShotOrGoalOpportunities": missed,
        },
        "teamStats": {
            "decisionByType": by_type,
            "timeline": timeline,
        },
    }


def split_for_index(index: int, total: int) -> str:
    train_cut = int(total * 0.7)
    val_cut = int(total * 0.85)
    if index < train_cut:
        return "train"
    if index < val_cut:
        return "val"
    return "test"


def create_category_truth(rng: random.Random) -> dict[str, float]:
    # Latent difficulty profile per match; build_up and ball_loss slightly more volatile.
    return {
        "build_up": clamp01(rng.betavariate(2.0, 2.2)),
        "ball_loss": clamp01(rng.betavariate(2.1, 2.0)),
        "progression": clamp01(rng.betavariate(2.0, 2.5)),
        "final_third": clamp01(rng.betavariate(1.9, 2.4)),
        "duels": clamp01(rng.betavariate(2.2, 2.6)),
        "pressing": clamp01(rng.betavariate(2.0, 2.8)),
    }


def build_labels(
    sample_id: str,
    category_truth: dict[str, float],
    needs_support: list[dict],
) -> dict:
    category_labels = []
    for category in TACTICAL_CATEGORIES:
        score = round(category_truth[category], 4)
        category_labels.append(
            {
                "category": category,
                "true_severity": score,
                "severity_band": severity_band(score),
                "is_problem": score >= 0.35,
            }
        )
    top_problems = sorted(category_truth.items(), key=lambda kv: kv[1], reverse=True)[:3]
    player_priority_labels = []
    for row in needs_support[:5]:
        player_priority_labels.append(
            {
                "player_name": row["player_name"],
                "true_priority_score": round(clamp01((1.0 - row["decisionScore"]) * 0.78), 4),
                "focus_categories": [
                    "build_up" if row.get("weakDecisionType") == "pass" else
                    "progression" if row.get("weakDecisionType") == "carry" else
                    "final_third"
                ],
            }
        )
    training_focus_labels = [
        {"category": cat, "priority": severity_band(score)}
        for cat, score in top_problems
    ]
    return {
        "sample_id": sample_id,
        "reviewer": "synthetic_generator",
        "review_date": "2026-04-25",
        "label_quality": "synthetic",
        "category_labels": category_labels,
        "top_problems_rank": [cat for cat, _ in top_problems],
        "player_priority_labels": player_priority_labels,
        "training_focus_labels": training_focus_labels,
        "notes": "Synthetic labels generated from latent category truth.",
    }


def generate_dataset(matches: int, seed: int, out_dir: Path) -> None:
    rng = random.Random(seed)
    samples_dir = out_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / "manifest.csv"
    labels_path = out_dir / "labels.jsonl"

    start_date = date(2025, 8, 1)

    with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file, labels_path.open(
        "w", encoding="utf-8"
    ) as labels_file:
        writer = csv.writer(manifest_file)
        writer.writerow(
            [
                "sample_id",
                "match_id",
                "team_id",
                "team_name",
                "match_date",
                "input1_path",
                "input2_path",
                "split",
                "data_quality",
            ]
        )

        for i in range(matches):
            match_id = 99000000 + i + 1
            team_id = 9000 + rng.randint(1, 30)
            team_name = rng.choice(TEAM_NAMES)
            match_day = start_date + timedelta(days=i * 3)
            sample_id = f"mock_{match_day.isoformat()}_{team_id}_{i+1:03d}"

            category_truth = create_category_truth(rng)
            input1 = make_input1(rng, match_id, team_id, team_name, category_truth)
            input2 = make_input2(rng, match_id, team_id, team_name, category_truth, match_day)

            input1_name = f"{sample_id}_input1.json"
            input2_name = f"{sample_id}_input2.json"
            input1_path = samples_dir / input1_name
            input2_path = samples_dir / input2_name

            with input1_path.open("w", encoding="utf-8") as f:
                json.dump(input1, f, ensure_ascii=False, indent=2)
            with input2_path.open("w", encoding="utf-8") as f:
                json.dump(input2, f, ensure_ascii=False, indent=2)

            split = split_for_index(i, matches)
            writer.writerow(
                [
                    sample_id,
                    match_id,
                    team_id,
                    team_name,
                    match_day.isoformat(),
                    f"samples/{input1_name}",
                    f"samples/{input2_name}",
                    split,
                    "synthetic",
                ]
            )

            label_line = build_labels(
                sample_id=sample_id,
                category_truth=category_truth,
                needs_support=input2["players"]["needsSupport"],
            )
            labels_file.write(json.dumps(label_line, ensure_ascii=False) + "\n")

    readme = out_dir / "README.md"
    readme.write_text(
        (
            "# Mock Tactical Fusion Dataset\n\n"
            f"- Generated on: 2026-04-25\n"
            f"- Matches: {matches}\n"
            f"- Seed: {seed}\n"
            "- Quality: synthetic\n\n"
            "Files:\n"
            "- `manifest.csv`\n"
            "- `labels.jsonl`\n"
            "- `samples/*_input1.json`\n"
            "- `samples/*_input2.json`\n"
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic tactical fusion dataset.")
    parser.add_argument("--matches", type=int, default=100, help="Number of mock matches.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("dataset") / "mock_100",
        help="Output dataset directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_dataset(matches=args.matches, seed=args.seed, out_dir=args.out_dir)
    print(f"Mock dataset generated at: {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()
