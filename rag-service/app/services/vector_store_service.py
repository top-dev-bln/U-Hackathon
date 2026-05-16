from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.errors import BadRequestError
from app.services.embedding_service import EmbeddedDocument
from app.vectorstores.faiss_store import FaissStore


class VectorStoreService:
    def __init__(self, settings: Settings) -> None:
        if settings.vector_store != "faiss":
            raise BadRequestError(
                f"Unsupported VECTOR_STORE={settings.vector_store}. Only faiss is supported in MVP."
            )
        self._store = FaissStore(settings.storage_dir)
        self.vector_store_name = "faiss"

    def save_match_index(
        self,
        *,
        match_id: int,
        embedded_documents: list[EmbeddedDocument],
        rebuild: bool,
    ) -> None:
        self._store.save_match_index(
            match_id=match_id,
            embedded_documents=embedded_documents,
            rebuild=rebuild,
        )

    def save_collection_index(
        self,
        *,
        collection_name: str,
        embedded_documents: list[EmbeddedDocument],
        rebuild: bool,
    ) -> None:
        self._store.save_collection_index(
            collection_name=collection_name,
            embedded_documents=embedded_documents,
            rebuild=rebuild,
        )

    def list_indexes(self) -> list[dict[str, Any]]:
        return self._store.list_indexes()

    def list_collections(self, *, prefix: str | None = None) -> list[dict[str, Any]]:
        return self._store.list_collections(prefix=prefix)

    def load_match_documents(self, match_id: int) -> list[dict[str, Any]]:
        return self._store.load_match_documents(match_id)

    def load_collection_documents(self, *, collection_name: str) -> list[dict[str, Any]]:
        return self._store.load_collection_documents(collection_name=collection_name)

    def delete_match_index(self, match_id: int) -> bool:
        return self._store.delete_match_index(match_id)

    def delete_collection_index(self, *, collection_name: str) -> bool:
        return self._store.delete_collection_index(collection_name=collection_name)
