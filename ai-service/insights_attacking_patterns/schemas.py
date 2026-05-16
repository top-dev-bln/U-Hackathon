from pydantic import BaseModel


class FlankBreakdown(BaseModel):
    left: int
    center: int
    right: int


class AttackType(BaseModel):
    label: str
    count: int
    withShot: int
    withGoal: int
    xgTotal: float


class PlayerAttacking(BaseModel):
    id: int
    name: str
    position: str | None
    attacks: int
    shots: int
    xgCreated: float
    preferredFlank: str | None


class AttackingPatternsResponse(BaseModel):
    match_id: int
    team_id: int
    period: str
    totalAttacks: int
    flankBreakdown: FlankBreakdown
    attackTypes: list[AttackType]
    avgXgPerAttack: float
    mostDangerousFlank: str
    insight: str
    players: list[PlayerAttacking]
    topAttacker: str | None
