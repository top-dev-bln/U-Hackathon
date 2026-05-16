from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RetrievedDocument(BaseModel):
    docId: str
    matchId: int | None = None
    teamId: int | None = None
    teamName: str | None = None
    sourceService: str
    sourceScope: str = Field(default="match", pattern="^(match|club)$")
    documentType: str
    category: str | None = None
    title: str | None = None
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float
