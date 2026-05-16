from pydantic import BaseModel


class PlayerPressing(BaseModel):
    id: int
    name: str
    position: str | None
    pressingDuels: int
    won: int
    efficiency: float
    inOpponentHalf: int
    intensityDrop: float


class PressingResponse(BaseModel):
    match_id: int
    team_id: int
    period: str
    teamPressingEfficiency: float
    firstHalfEfficiency: float
    secondHalfEfficiency: float
    intensityDrop: float
    insight: str
    players: list[PlayerPressing]
    topPresser: str | None
