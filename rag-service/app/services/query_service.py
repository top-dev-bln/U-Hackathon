from __future__ import annotations

import time

from app.core.config import Settings
from app.core.errors import InternalServerError
from app.core.logging import get_logger
from app.schemas.query import (
    ChatHistoryMessage,
    RagQueryDebugResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagSourceRef,
    SessionResetResponse,
)
from app.services.chat_history_service import ChatHistoryService
from app.services.context_service import ContextService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LlmService
from app.services.retrieval_service import RetrievalService

logger = get_logger(__name__)


class QueryService:
    def __init__(
        self,
        *,
        settings: Settings,
        embedding_service: EmbeddingService,
        retrieval_service: RetrievalService,
        context_service: ContextService,
        chat_history_service: ChatHistoryService,
        llm_service: LlmService,
    ) -> None:
        self._settings = settings
        self._embedding = embedding_service
        self._retrieval = retrieval_service
        self._context = context_service
        self._history = chat_history_service
        self._llm = llm_service

    def query(self, request: RagQueryRequest) -> RagQueryResponse:
        result = self._query_internal(request=request, debug=False)
        if not isinstance(result, RagQueryResponse):
            raise InternalServerError("Expected RagQueryResponse in query().")
        return result

    def query_debug(self, request: RagQueryRequest) -> RagQueryDebugResponse:
        result = self._query_internal(request=request, debug=True)
        if not isinstance(result, RagQueryDebugResponse):
            raise InternalServerError("Expected RagQueryDebugResponse in query_debug().")
        return result

    def _query_internal(
        self,
        *,
        request: RagQueryRequest,
        debug: bool,
    ) -> RagQueryResponse | RagQueryDebugResponse:
        started = time.perf_counter()
        warnings: list[str] = []
        session_id = request.sessionId
        logger.info("rag_query_received matchId=%s sessionId=%s", request.matchId, session_id)

        top_k = request.topK or self._settings.rag_top_k_default
        top_k = max(1, min(top_k, self._settings.rag_top_k_max))
        question = request.question.strip()
        recent_history = self._history.get_recent(session_id)

        t_embed_start = time.perf_counter()
        query_vector = self._embedding.embed_text(question)
        embed_ms = int((time.perf_counter() - t_embed_start) * 1000)
        logger.info(
            "rag_query_embedded matchId=%s sessionId=%s dim=%s embedMs=%s",
            request.matchId,
            session_id,
            len(query_vector),
            embed_ms,
        )

        t_retrieval_start = time.perf_counter()
        retrieved, retrieval_warnings = self._retrieval.retrieve(
            match_id=request.matchId,
            query_vector=query_vector,
            top_k=top_k,
            club_key=request.clubKey,
            include_club_knowledge=request.includeClubKnowledge,
            team_id=request.teamId,
            document_types=request.documentTypes,
            min_score=request.minScore,
        )
        retrieval_ms = int((time.perf_counter() - t_retrieval_start) * 1000)
        warnings.extend(retrieval_warnings)
        retrieved_dynamic_count = sum(1 for doc in retrieved if doc.sourceScope == "match")
        retrieved_static_count = sum(1 for doc in retrieved if doc.sourceScope == "club")
        merged_count = len(retrieved)
        logger.info(
            (
                "rag_query_retrieved matchId=%s sessionId=%s retrieved=%s "
                "retrieved_dynamic_count=%s retrieved_static_count=%s merged_count=%s retrievalMs=%s"
            ),
            request.matchId,
            session_id,
            len(retrieved),
            retrieved_dynamic_count,
            retrieved_static_count,
            merged_count,
            retrieval_ms,
        )

        t_context_start = time.perf_counter()
        context, context_docs, context_warnings = self._context.build_context(
            session_id=session_id,
            question=question,
            retrieved=retrieved,
            chat_history=recent_history,
        )
        context_ms = int((time.perf_counter() - t_context_start) * 1000)
        warnings.extend(context_warnings)

        t_llm_start = time.perf_counter()
        answer, model_used, llm_warnings = self._llm.answer(
            question=question,
            context=context,
            sources=context_docs,
        )
        llm_ms = int((time.perf_counter() - t_llm_start) * 1000)
        answer = self._append_source_citations(answer=answer, sources=context_docs)
        warnings.extend(llm_warnings)
        logger.info(
            (
                "rag_query_answered matchId=%s sessionId=%s model=%s "
                "contextDocs=%s contextMs=%s llmMs=%s"
            ),
            request.matchId,
            session_id,
            model_used,
            len(context_docs),
            context_ms,
            llm_ms,
        )

        self._history.append_user(session_id, question)
        self._history.append_assistant(session_id, answer)

        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            (
                "rag_query_completed matchId=%s sessionId=%s "
                "embedMs=%s retrievalMs=%s contextMs=%s llmMs=%s totalMs=%s"
            ),
            request.matchId,
            session_id,
            embed_ms,
            retrieval_ms,
            context_ms,
            llm_ms,
            elapsed,
        )
        source_refs = [
            RagSourceRef(
                docId=doc.docId,
                documentType=doc.documentType,
                title=doc.title,
                score=doc.score,
                sourceService=doc.sourceService,
                sourceScope=doc.sourceScope,
                page=(doc.metadata.get("page") if isinstance(doc.metadata, dict) else None),
            )
            for doc in context_docs
        ]

        if debug:
            return RagQueryDebugResponse(
                sessionId=session_id,
                matchId=request.matchId,
                answer=answer,
                retrievedCount=len(context_docs),
                sources=source_refs,
                warnings=warnings,
                latencyMs=elapsed,
                model=model_used,
                context=context,
                systemPrompt=self._llm.system_prompt,
                retrievedDocuments=context_docs,
            )

        return RagQueryResponse(
            sessionId=session_id,
            matchId=request.matchId,
            answer=answer,
            retrievedCount=len(context_docs),
            sources=source_refs,
            warnings=warnings,
            latencyMs=elapsed,
            model=model_used,
        )

    def list_matches(self) -> list[dict]:
        return self._retrieval.list_matches()

    def list_sources(self, match_id: int, limit: int = 100) -> list:
        return self._retrieval.list_sources(match_id=match_id, limit=limit)

    def list_club_collections(self) -> list[dict]:
        return self._retrieval.list_club_collections()

    def list_club_sources(self, club_key: str, limit: int = 100) -> list:
        return self._retrieval.list_club_sources(club_key=club_key, limit=limit)

    def get_session_history(self, session_id: str) -> list[ChatHistoryMessage]:
        return self._history.get_recent(session_id)

    def reset_session(self, session_id: str) -> SessionResetResponse:
        removed = self._history.clear(session_id)
        return SessionResetResponse(
            sessionId=session_id,
            cleared=True,
            messagesRemoved=removed,
        )

    @staticmethod
    def _append_source_citations(answer: str, sources: list) -> str:
        if not answer.strip() or not sources:
            return answer
        if "Surse utilizate:" in answer:
            return answer

        seen: set[str] = set()
        chunks: list[str] = []
        for doc in sources:
            if doc.docId in seen:
                continue
            seen.add(doc.docId)
            page = None
            if isinstance(doc.metadata, dict):
                if isinstance(doc.metadata.get("page"), int):
                    page = int(doc.metadata["page"])
                else:
                    pages = doc.metadata.get("pages")
                    if isinstance(pages, list) and pages and isinstance(pages[0], int):
                        page = int(pages[0])
            title = (doc.title or "").strip()
            if page is not None:
                part = f"{doc.docId} ({title or doc.documentType}, p.{page}, {doc.sourceScope})"
            else:
                part = f"{doc.docId} ({title or doc.documentType}, {doc.sourceScope})"
            chunks.append(part)
            if len(chunks) >= 4:
                break

        if not chunks:
            return answer
        return answer.rstrip() + "\n\nSurse utilizate: " + "; ".join(chunks) + "."
