from pydantic import BaseModel


class PlayerLineBreaking(BaseModel):
    id: int
    name: str
    position: str | None
    totalRuns: int
    progressiveCarries: int
    progressivePasses: int
    avgProgressionX: float
    intoFinalThird: int
    intoBox: int
    led_to_shot: int


class LineBreakingResponse(BaseModel):
    match_id: int
    team_id: int
    period: str
    totalLineBreakingActions: int
    progressiveCarries: int
    progressivePasses: int
    intoFinalThird: int
    intoBox: int
    led_to_shot: int
    insight: str
    players: list[PlayerLineBreaking]
    topRunner: str | None
