from pydantic import BaseModel


class PlayerInfo(BaseModel):
    id: int
    name: str
    position: str


class TeamInfo(BaseModel):
    id: int
    name: str


class Grid(BaseModel):
    cols: int
    rows: int
    cells: list[list[int]]


class Zones(BaseModel):
    def_third: int
    mid_third: int
    att_third: int


class Flanks(BaseModel):
    left: int
    center: int
    right: int


class Stats(BaseModel):
    total_touches: int
    avg_x: float
    avg_y: float
    zones: Zones
    flanks: Flanks
    receptions: int


class PlayerProfileResponse(BaseModel):
    match_id: int
    period: str
    player: PlayerInfo
    team: TeamInfo
    grid: Grid
    stats: Stats
