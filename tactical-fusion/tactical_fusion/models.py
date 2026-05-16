from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

TacticalCategory = Literal[
    "build_up",
    "ball_loss",
    "progression",
    "final_third",
    "duels",
    "pressing",
]


@dataclass(frozen=True)
class BaselineSignal:
    category: TacticalCategory
    severity: float
    metric: str
    signal_id: str


@dataclass(frozen=True)
class DecisionSignal:
    category: TacticalCategory
    severity: float
    players: list[str] = field(default_factory=list)
    decision_type: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class FusedSignal:
    category: TacticalCategory
    baseline_score: float
    decision_score: float
    combined_score: float
    confidence: float
    players: list[str] = field(default_factory=list)
    baseline_evidence: list[str] = field(default_factory=list)
    decision_evidence: list[str] = field(default_factory=list)
    evidence_count: int = 0


@dataclass(frozen=True)
class Insight:
    type: str
    category: TacticalCategory
    severity: str
    score: float
    confidence: float
    message: str
    recommendation: str
    players: list[str] = field(default_factory=list)
    evidence: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PlayerPriority:
    player: str
    priority_score: float
    reasons: list[str]
    focus_categories: list[TacticalCategory]
    recommendedAction: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TrainingFocus:
    category: TacticalCategory
    priority: str
    objective: str
    drill: str

    def to_dict(self) -> dict:
        return asdict(self)
