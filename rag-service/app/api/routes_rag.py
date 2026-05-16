from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_query_service
from app.schemas.query import (
    ChatHistoryMessage,
    RagQueryDebugResponse,
    RagQueryRequest,
    RagQueryResponse,
    SessionResetResponse,
)
from app.schemas.retrieval import RetrievedDocument
from app.services.query_service import QueryService

router = APIRouter(tags=["rag"])


@router.post("/rag/query", response_model=RagQueryResponse)
def rag_query(
    request: RagQueryRequest,
    service: QueryService = Depends(get_query_service),
) -> RagQueryResponse:
    return service.query(request)


@router.post("/rag/query/debug", response_model=RagQueryDebugResponse)
def rag_query_debug(
    request: RagQueryRequest,
    service: QueryService = Depends(get_query_service),
) -> RagQueryDebugResponse:
    return service.query_debug(request)


@router.get("/rag/matches")
def rag_list_matches(
    service: QueryService = Depends(get_query_service),
) -> list[dict]:
    return service.list_matches()


@router.get("/rag/clubs")
def rag_list_clubs(
    service: QueryService = Depends(get_query_service),
) -> list[dict]:
    return service.list_club_collections()


@router.get("/rag/matches/{match_id}/sources", response_model=list[RetrievedDocument])
def rag_list_sources(
    match_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    service: QueryService = Depends(get_query_service),
) -> list[RetrievedDocument]:
    return service.list_sources(match_id=match_id, limit=limit)


@router.get("/rag/clubs/{club_key}/sources", response_model=list[RetrievedDocument])
def rag_list_club_sources(
    club_key: str,
    limit: int = Query(default=100, ge=1, le=500),
    service: QueryService = Depends(get_query_service),
) -> list[RetrievedDocument]:
    return service.list_club_sources(club_key=club_key, limit=limit)


@router.get("/rag/sessions/{session_id}/history", response_model=list[ChatHistoryMessage])
def rag_get_history(
    session_id: str,
    service: QueryService = Depends(get_query_service),
) -> list[ChatHistoryMessage]:
    return service.get_session_history(session_id)


@router.post("/rag/sessions/{session_id}/reset", response_model=SessionResetResponse)
def rag_reset_session(
    session_id: str,
    service: QueryService = Depends(get_query_service),
) -> SessionResetResponse:
    return service.reset_session(session_id)
