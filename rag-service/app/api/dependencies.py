from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.chat_history_service import ChatHistoryService
from app.services.club_knowledge_service import ClubKnowledgeService
from app.services.context_service import ContextService
from app.services.document_builder_service import DocumentBuilderService
from app.services.embedding_service import EmbeddingService
from app.services.indexing_service import IndexingService
from app.services.llm_service import LlmService
from app.services.query_service import QueryService
from app.services.retrieval_service import RetrievalService
from app.services.vector_store_service import VectorStoreService


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    return EmbeddingService(settings)


@lru_cache(maxsize=1)
def get_indexing_service() -> IndexingService:
    settings = get_settings()
    document_builder = DocumentBuilderService(max_player_documents=settings.max_player_documents)
    club_knowledge_service = ClubKnowledgeService()
    embedding_service = get_embedding_service()
    vector_store_service = VectorStoreService(settings)
    return IndexingService(
        document_builder=document_builder,
        club_knowledge_service=club_knowledge_service,
        embedding_service=embedding_service,
        vector_store=vector_store_service,
    )


@lru_cache(maxsize=1)
def get_chat_history_service() -> ChatHistoryService:
    settings = get_settings()
    return ChatHistoryService(
        max_messages=settings.rag_history_max_messages,
        max_message_chars=settings.rag_history_message_max_chars,
    )


@lru_cache(maxsize=1)
def get_query_service() -> QueryService:
    settings = get_settings()
    embedding_service = get_embedding_service()
    retrieval_service = RetrievalService(settings)
    context_service = ContextService(settings)
    chat_history_service = get_chat_history_service()
    llm_service = LlmService(settings)
    return QueryService(
        settings=settings,
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
        context_service=context_service,
        chat_history_service=chat_history_service,
        llm_service=llm_service,
    )
