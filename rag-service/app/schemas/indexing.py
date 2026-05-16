from __future__ import annotations

from pydantic import BaseModel

from app.schemas.documents import DocumentPreview, RagDocument


class BuildDocumentsResponse(BaseModel):
    matchId: int
    teamId: int | None = None
    teamName: str | None = None
    documentsCreated: int
    warnings: list[str]
    documents: list[RagDocument]


class IndexMatchResponse(BaseModel):
    matchId: int
    teamId: int | None = None
    teamName: str | None = None
    status: str
    documentsCreated: int
    embeddingsCreated: int
    vectorStore: str
    collectionName: str
    documentTypes: dict[str, int]
    warnings: list[str]
    documentPreview: list[DocumentPreview]


class IndexedMatchEntry(BaseModel):
    matchId: int
    collectionName: str
    documentsCount: int
    vectorStore: str


class BuildClubDocumentsResponse(BaseModel):
    clubKey: str
    teamId: int | None = None
    teamName: str | None = None
    documentsCreated: int
    warnings: list[str]
    documents: list[RagDocument]


class IndexClubResponse(BaseModel):
    clubKey: str
    teamId: int | None = None
    teamName: str | None = None
    status: str
    documentsCreated: int
    embeddingsCreated: int
    vectorStore: str
    collectionName: str
    documentTypes: dict[str, int]
    warnings: list[str]
    documentPreview: list[DocumentPreview]


class IndexedCollectionEntry(BaseModel):
    collectionName: str
    documentsCount: int
    vectorStore: str
