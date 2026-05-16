from __future__ import annotations

import time
from collections import Counter

from app.core.errors import BadRequestError, InternalServerError
from app.core.logging import get_logger
from app.schemas.documents import DocumentPreview, RagDocument
from app.schemas.indexing import (
    BuildClubDocumentsResponse,
    BuildDocumentsResponse,
    IndexedCollectionEntry,
    IndexClubResponse,
    IndexMatchResponse,
    IndexedMatchEntry,
)
from app.schemas.input_bundle import IndexClubKnowledgeRequest, IndexMatchRequest
from app.services.club_knowledge_service import ClubKnowledgeService
from app.services.document_builder_service import DocumentBuilderService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.utils.ids import slugify

logger = get_logger(__name__)


class IndexingService:
    def __init__(
        self,
        *,
        document_builder: DocumentBuilderService,
        club_knowledge_service: ClubKnowledgeService,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
    ) -> None:
        self._document_builder = document_builder
        self._club_knowledge = club_knowledge_service
        self._embedding_service = embedding_service
        self._vector_store = vector_store

    def build_documents_only(self, request: IndexMatchRequest) -> BuildDocumentsResponse:
        documents, warnings = self._document_builder.build_documents(request)
        return BuildDocumentsResponse(
            matchId=request.matchId,
            teamId=request.teamId,
            teamName=request.teamName,
            documentsCreated=len(documents),
            warnings=warnings,
            documents=documents,
        )

    def index_match(self, request: IndexMatchRequest) -> IndexMatchResponse:
        started = time.perf_counter()
        requested_store = request.options.vectorStore.lower()
        if requested_store != self._vector_store.vector_store_name:
            raise BadRequestError(
                f"Requested vector store '{requested_store}' does not match configured store "
                f"'{self._vector_store.vector_store_name}'."
            )
        logger.info(
            "received_index_request matchId=%s teamId=%s",
            request.matchId,
            request.teamId,
        )

        documents, warnings = self._document_builder.build_documents(request)
        if not documents:
            raise BadRequestError("No documents generated from provided outputs.")

        logger.info(
            "documents_built matchId=%s documentCount=%s warningsCount=%s",
            request.matchId,
            len(documents),
            len(warnings),
        )

        embedded_docs = self._embedding_service.embed_documents(documents)
        if len(embedded_docs) != len(documents):
            raise InternalServerError(
                "Embedding generation mismatch: embeddings count does not match documents count."
            )

        logger.info(
            "embeddings_created matchId=%s embeddingCount=%s dim=%s",
            request.matchId,
            len(embedded_docs),
            self._embedding_service.embedding_dimension,
        )

        self._vector_store.save_match_index(
            match_id=request.matchId,
            embedded_documents=embedded_docs,
            rebuild=request.options.rebuild,
        )
        logger.info(
            "vector_index_saved matchId=%s vectorStore=%s",
            request.matchId,
            self._vector_store.vector_store_name,
        )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        doc_type_counts = dict(Counter(doc.documentType for doc in documents))
        response = IndexMatchResponse(
            matchId=request.matchId,
            teamId=request.teamId,
            teamName=request.teamName,
            status="indexed",
            documentsCreated=len(documents),
            embeddingsCreated=len(embedded_docs),
            vectorStore=self._vector_store.vector_store_name,
            collectionName=f"match_{request.matchId}",
            documentTypes=doc_type_counts,
            warnings=warnings,
            documentPreview=self._build_preview(documents),
        )
        logger.info(
            "index_request_finished matchId=%s status=%s documentCount=%s durationMs=%s warningsCount=%s",
            request.matchId,
            response.status,
            response.documentsCreated,
            elapsed_ms,
            len(warnings),
        )
        return response

    def list_matches(self) -> list[IndexedMatchEntry]:
        entries = self._vector_store.list_indexes()
        return [IndexedMatchEntry(**entry) for entry in entries]

    def build_club_documents_only(self, request: IndexClubKnowledgeRequest) -> BuildClubDocumentsResponse:
        documents, warnings = self._club_knowledge.build_documents(request)
        return BuildClubDocumentsResponse(
            clubKey=request.clubKey,
            teamId=request.teamId,
            teamName=request.teamName,
            documentsCreated=len(documents),
            warnings=warnings,
            documents=documents,
        )

    def index_club_knowledge(self, request: IndexClubKnowledgeRequest) -> IndexClubResponse:
        started = time.perf_counter()
        requested_store = request.options.vectorStore.lower()
        if requested_store != self._vector_store.vector_store_name:
            raise BadRequestError(
                f"Requested vector store '{requested_store}' does not match configured store "
                f"'{self._vector_store.vector_store_name}'."
            )

        documents, warnings = self._club_knowledge.build_documents(request)
        if not documents:
            raise BadRequestError("No club knowledge documents generated from provided PDF.")

        embedded_docs = self._embedding_service.embed_documents(documents)
        if len(embedded_docs) != len(documents):
            raise InternalServerError(
                "Embedding generation mismatch: embeddings count does not match documents count."
            )

        safe_club = slugify(request.clubKey)
        collection_name = f"club_knowledge_{safe_club}"
        self._vector_store.save_collection_index(
            collection_name=collection_name,
            embedded_documents=embedded_docs,
            rebuild=request.options.rebuild,
        )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        doc_type_counts = dict(Counter(doc.documentType for doc in documents))
        response = IndexClubResponse(
            clubKey=request.clubKey,
            teamId=request.teamId,
            teamName=request.teamName,
            status="indexed",
            documentsCreated=len(documents),
            embeddingsCreated=len(embedded_docs),
            vectorStore=self._vector_store.vector_store_name,
            collectionName=collection_name,
            documentTypes=doc_type_counts,
            warnings=warnings,
            documentPreview=self._build_preview(documents),
        )
        logger.info(
            "club_index_finished clubKey=%s status=%s documents=%s durationMs=%s warningsCount=%s",
            request.clubKey,
            response.status,
            response.documentsCreated,
            elapsed_ms,
            len(warnings),
        )
        return response

    def list_club_collections(self) -> list[IndexedCollectionEntry]:
        entries = self._vector_store.list_collections(prefix="club_knowledge_")
        return [IndexedCollectionEntry(**entry) for entry in entries]

    def get_club_documents(self, club_key: str) -> list[RagDocument]:
        collection_name = f"club_knowledge_{slugify(club_key)}"
        rows = self._vector_store.load_collection_documents(collection_name=collection_name)
        cleaned = []
        for row in rows:
            if isinstance(row, dict) and "vectorId" in row:
                row = {k: v for k, v in row.items() if k != "vectorId"}
            cleaned.append(RagDocument.model_validate(row))
        return cleaned

    def get_match_documents(self, match_id: int) -> list[RagDocument]:
        rows = self._vector_store.load_match_documents(match_id)
        cleaned = []
        for row in rows:
            if isinstance(row, dict) and "vectorId" in row:
                row = {k: v for k, v in row.items() if k != "vectorId"}
            cleaned.append(RagDocument.model_validate(row))
        return cleaned

    @staticmethod
    def _build_preview(documents: list[RagDocument], max_items: int = 5) -> list[DocumentPreview]:
        preview: list[DocumentPreview] = []
        for doc in documents[:max_items]:
            preview.append(
                DocumentPreview(
                    docId=doc.docId,
                    type=doc.documentType,
                    textPreview=doc.text[:220].strip(),
                )
            )
        return preview
