from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_indexing_service
from app.schemas.documents import RagDocument
from app.schemas.indexing import (
    BuildClubDocumentsResponse,
    BuildDocumentsResponse,
    IndexedCollectionEntry,
    IndexClubResponse,
    IndexMatchResponse,
    IndexedMatchEntry,
)
from app.schemas.input_bundle import IndexClubKnowledgeRequest, IndexMatchRequest
from app.services.indexing_service import IndexingService

router = APIRouter(tags=["indexing"])


@router.post("/documents/build", response_model=BuildDocumentsResponse)
def build_documents(
    request: IndexMatchRequest,
    service: IndexingService = Depends(get_indexing_service),
) -> BuildDocumentsResponse:
    return service.build_documents_only(request)


@router.post("/index/match", response_model=IndexMatchResponse)
def index_match(
    request: IndexMatchRequest,
    service: IndexingService = Depends(get_indexing_service),
) -> IndexMatchResponse:
    return service.index_match(request)


@router.get("/index/matches", response_model=list[IndexedMatchEntry])
def list_indexed_matches(
    service: IndexingService = Depends(get_indexing_service),
) -> list[IndexedMatchEntry]:
    return service.list_matches()


@router.get("/index/matches/{match_id}/documents", response_model=list[RagDocument])
def get_indexed_documents(
    match_id: int,
    service: IndexingService = Depends(get_indexing_service),
) -> list[RagDocument]:
    return service.get_match_documents(match_id)


@router.post("/documents/build/club", response_model=BuildClubDocumentsResponse)
def build_club_documents(
    request: IndexClubKnowledgeRequest,
    service: IndexingService = Depends(get_indexing_service),
) -> BuildClubDocumentsResponse:
    return service.build_club_documents_only(request)


@router.post("/index/club", response_model=IndexClubResponse)
def index_club(
    request: IndexClubKnowledgeRequest,
    service: IndexingService = Depends(get_indexing_service),
) -> IndexClubResponse:
    return service.index_club_knowledge(request)


@router.get("/index/clubs", response_model=list[IndexedCollectionEntry])
def list_club_indexes(
    service: IndexingService = Depends(get_indexing_service),
) -> list[IndexedCollectionEntry]:
    return service.list_club_collections()


@router.get("/index/clubs/{club_key}/documents", response_model=list[RagDocument])
def get_club_documents(
    club_key: str,
    service: IndexingService = Depends(get_indexing_service),
) -> list[RagDocument]:
    return service.get_club_documents(club_key)
