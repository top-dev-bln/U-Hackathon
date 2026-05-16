from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.retrieval import RetrievedDocument


class RagQueryRequest(BaseModel):
    sessionId: str = Field(min_length=3, max_length=128)
    question: str = Field(min_length=3, max_length=2000)
    matchId: int = Field(gt=0)
    clubKey: str | None = Field(default=None, min_length=2, max_length=64)
    includeClubKnowledge: bool = False
    teamId: int | None = Field(default=None, gt=0)
    topK: int | None = Field(default=None, ge=1, le=100)
    documentTypes: list[str] | None = None
    minScore: float | None = None
    includeDebug: bool = False

    @field_validator("question")
    @classmethod
    def _normalize_question(cls, value: str) -> str:
        text = " ".join(value.split()).strip()
        if not text:
            raise ValueError("Question must not be empty.")
        return text

    @field_validator("sessionId")
    @classmethod
    def _normalize_session_id(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("sessionId must not be empty.")
        return text

    @field_validator("documentTypes")
    @classmethod
    def _normalize_doc_types(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned or None

    @field_validator("clubKey")
    @classmethod
    def _normalize_club_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        text = value.strip().lower()
        return text or None


class RagSourceRef(BaseModel):
    docId: str
    documentType: str
    title: str | None = None
    score: float
    sourceService: str
    sourceScope: str = Field(pattern="^(match|club)$")
    page: int | None = None


class RagQueryResponse(BaseModel):
    sessionId: str
    matchId: int
    answer: str
    retrievedCount: int
    sources: list[RagSourceRef]
    warnings: list[str]
    latencyMs: int
    model: str


class RagQueryDebugResponse(RagQueryResponse):
    context: str
    systemPrompt: str
    retrievedDocuments: list[RetrievedDocument]


class ChatHistoryMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    text: str
    timestamp: datetime


class SessionResetResponse(BaseModel):
    sessionId: str
    cleared: bool
    messagesRemoved: int
