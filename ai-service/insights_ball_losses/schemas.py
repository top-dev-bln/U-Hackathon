from pydantic import BaseModel


class TeamInfo(BaseModel):
    id: int
    name: str


class LossEvent(BaseModel):
    minute: int
    second: int
    period: str | None
    player_id: int | None
    player_name: str | None
    player_position: str | None
    x: float | None
    y: float | None
    zone: str  # defensive_third | middle_third | attacking_third
    type: str  # inaccurate_pass | duel_lost | loss_tag


class PlayerLossSummary(BaseModel):
    id: int
    name: str
    position: str | None
    losses: int
    dangerous_losses: int  # losses in own defensive third


class Grid(BaseModel):
    cols: int
    rows: int
    cells: list[list[int]]


class BallLossesResponse(BaseModel):
    match_id: int
    team: TeamInfo
    period: str
    total_losses: int
    by_zone: dict[str, int]
    by_type: dict[str, int]
    by_player: list[PlayerLossSummary]
    grid: Grid
    danger_score: float
    events: list[LossEvent]
