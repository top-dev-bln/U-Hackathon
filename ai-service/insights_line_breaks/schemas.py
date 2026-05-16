from pydantic import BaseModel


class TeamInfo(BaseModel):
    id: int
    name: str


class LineBreakEvent(BaseModel):
    minute: int
    second: int
    period: str | None
    type: str  # progressive | through
    accurate: bool
    passer_id: int | None
    passer_name: str | None
    passer_position: str | None
    recipient_id: int | None
    recipient_name: str | None
    recipient_position: str | None
    start_x: float | None
    start_y: float | None
    end_x: float | None
    end_y: float | None
    length: float | None
    target_zone: str  # defensive_third | middle_third | attacking_third


class PlayerLineBreakSummary(BaseModel):
    id: int
    name: str
    position: str | None
    attempts: int
    completed: int
    completion_rate: float


class LineBreaksResponse(BaseModel):
    match_id: int
    team: TeamInfo
    period: str
    total_attempts: int
    total_completed: int
    completion_rate: float
    by_type: dict[str, int]
    by_target_zone: dict[str, int]
    by_player: list[PlayerLineBreakSummary]
    events: list[LineBreakEvent]
