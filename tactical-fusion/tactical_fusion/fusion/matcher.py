from __future__ import annotations

from collections import Counter, defaultdict

from tactical_fusion.models import BaselineSignal, DecisionSignal, FusedSignal, TacticalCategory

BASELINE_WEIGHT = 0.55
DECISION_WEIGHT = 0.45


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def fuse_signals(
    baseline_signals: list[BaselineSignal],
    decision_signals: list[DecisionSignal],
    baseline_weight: float = BASELINE_WEIGHT,
    decision_weight: float = DECISION_WEIGHT,
) -> list[FusedSignal]:
    weight_sum = baseline_weight + decision_weight
    if weight_sum <= 0:
        baseline_weight, decision_weight = BASELINE_WEIGHT, DECISION_WEIGHT
        weight_sum = baseline_weight + decision_weight
    baseline_weight /= weight_sum
    decision_weight /= weight_sum

    categories: set[TacticalCategory] = set()
    baseline_by_category: dict[TacticalCategory, list[BaselineSignal]] = defaultdict(list)
    decision_by_category: dict[TacticalCategory, list[DecisionSignal]] = defaultdict(list)

    for signal in baseline_signals:
        categories.add(signal.category)
        baseline_by_category[signal.category].append(signal)
    for signal in decision_signals:
        categories.add(signal.category)
        decision_by_category[signal.category].append(signal)

    fused: list[FusedSignal] = []
    for category in sorted(categories):
        baseline_list = baseline_by_category.get(category, [])
        decision_list = decision_by_category.get(category, [])

        baseline_score = _avg([signal.severity for signal in baseline_list])
        decision_score = _avg([signal.severity for signal in decision_list])
        combined_score = baseline_weight * baseline_score + decision_weight * decision_score

        player_counter: Counter[str] = Counter()
        for signal in decision_list:
            for player in signal.players:
                player_counter[player] += 1
        ranked_players = [
            player
            for player, _ in sorted(
                player_counter.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

        baseline_evidence = sorted(
            {signal.signal_id for signal in baseline_list if signal.signal_id}
        )
        decision_evidence = sorted(
            {
                (signal.reason or signal.decision_type or "decision_signal")
                for signal in decision_list
            }
        )

        evidence_count = len(baseline_list) + len(decision_list)
        confidence = min(0.95, evidence_count / 6.0)

        fused.append(
            FusedSignal(
                category=category,
                baseline_score=baseline_score,
                decision_score=decision_score,
                combined_score=combined_score,
                confidence=confidence,
                players=ranked_players,
                baseline_evidence=baseline_evidence,
                decision_evidence=decision_evidence,
                evidence_count=evidence_count,
            )
        )

    fused.sort(key=lambda row: row.combined_score, reverse=True)
    return fused
