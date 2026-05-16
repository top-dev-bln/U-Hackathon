from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class RagDocument(BaseModel):
    docId: str = Field(min_length=3)
    matchId: int | None = Field(default=None, gt=0)
    teamId: int | None = None
    teamName: str | None = None
    sourceService: str = Field(min_length=3)
    documentType: str = Field(min_length=3)
    category: str | None = None
    title: str | None = None
    text: str = Field(min_length=10)
    metadata: dict[str, Any]

    @field_validator("text")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Document text must not be empty.")
        return text


class DocumentPreview(BaseModel):
    docId: str
    type: str
    textPreview: str
