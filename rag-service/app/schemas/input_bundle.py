from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ModelOutputs(BaseModel):
    fusion: dict[str, Any] | None = None
    tacticalBaseline: dict[str, Any] | None = None
    tacticalIntelligence: dict[str, Any] | None = None
    decisionQuality: dict[str, Any] | None = None
    playerProfiles: list[dict[str, Any]] | None = None
    pressing: dict[str, Any] | None = None
    passingNetwork: dict[str, Any] | None = None
    passingNewtork: dict[str, Any] | None = None
    lineBreaks: dict[str, Any] | None = None
    line_breaks: dict[str, Any] | None = None
    ballLosses: dict[str, Any] | None = None
    ball_losses: dict[str, Any] | None = None
    attackingPatterns: dict[str, Any] | None = None
    attacking_patterns: dict[str, Any] | None = None


class IndexOptions(BaseModel):
    vectorStore: str = Field(default="faiss")
    rebuild: bool = True
    topNPhases: int = Field(default=10, ge=1, le=100)
    includeDebugDocuments: bool = False


class IndexMatchRequest(BaseModel):
    matchId: int = Field(..., gt=0)
    teamId: int | None = Field(default=None, gt=0)
    teamName: str | None = None
    source: str = "generated_models"
    outputs: ModelOutputs
    options: IndexOptions = Field(default_factory=IndexOptions)

    @field_validator("teamName")
    @classmethod
    def _normalize_team_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        text = value.strip()
        return text or None


class ClubIndexOptions(BaseModel):
    vectorStore: str = Field(default="faiss")
    rebuild: bool = True
    maxPages: int | None = Field(default=None, ge=1, le=2000)
    maxCharsPerPage: int = Field(default=3000, ge=400, le=20000)


class IndexClubKnowledgeRequest(BaseModel):
    clubKey: str = Field(min_length=2, max_length=64)
    teamId: int | None = Field(default=None, gt=0)
    teamName: str | None = None
    pdfPath: str = Field(default="ANALIZA SPORTIVA.pdf", min_length=3, max_length=500)
    source: str = "club_pdf"
    options: ClubIndexOptions = Field(default_factory=ClubIndexOptions)

    @field_validator("clubKey")
    @classmethod
    def _normalize_club_key(cls, value: str) -> str:
        text = value.strip().lower()
        if not text:
            raise ValueError("clubKey must not be empty.")
        return text

    @field_validator("teamName")
    @classmethod
    def _normalize_club_team_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        text = value.strip()
        return text or None

    @field_validator("pdfPath")
    @classmethod
    def _normalize_pdf_path(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("pdfPath must not be empty.")
        return text
