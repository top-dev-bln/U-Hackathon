from pydantic import BaseModel


class Node(BaseModel):
    id: int
    name: str
    position: str
    x: float
    y: float
    touches: int


class Edge(BaseModel):
    source: int
    target: int
    weight: int


class TeamInfo(BaseModel):
    id: int
    name: str


class PassingNetworkResponse(BaseModel):
    match_id: int
    team: TeamInfo
    period: str
    cutoff_minute: int | None
    nodes: list[Node]
    edges: list[Edge]
