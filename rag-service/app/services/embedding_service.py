from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.core.errors import InternalServerError
from app.schemas.documents import RagDocument
from app.utils.safe_get import as_list
from app.utils.text_formatting import safe_text


@dataclass
class EmbeddedDocument:
    document: RagDocument
    embedding: list[float]


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any | None = None
        self._embedding_dim: int | None = None

    @property
    def embedding_dimension(self) -> int | None:
        return self._embedding_dim

    def embed_text(self, text: str) -> list[float]:
        normalized = text.strip()
        if not normalized:
            raise InternalServerError("Embedding rejected empty text.")

        if self._settings.embedding_provider != "sentence_transformers":
            raise InternalServerError(
                f"Unsupported EMBEDDING_PROVIDER={self._settings.embedding_provider}. "
                "Use sentence_transformers for this MVP."
            )

        self._ensure_model_loaded()
        if self._model is None:
            raise InternalServerError("Embedding model is not loaded.")
        vector = self._model.encode(normalized, normalize_embeddings=True)
        result = [float(x) for x in vector.tolist()]
        self._update_dimension(result)
        return result

    def embed_documents(self, documents: list[RagDocument]) -> list[EmbeddedDocument]:
        if not documents:
            return []

        embedding_inputs = [self._build_embedding_input(doc) for doc in documents]
        for value in embedding_inputs:
            if not value.strip():
                raise InternalServerError("Encountered empty embedding payload.")

        self._ensure_model_loaded()
        if self._model is None:
            raise InternalServerError("Embedding model is not loaded.")
        vectors = self._model.encode(embedding_inputs, normalize_embeddings=True)
        embedded_docs: list[EmbeddedDocument] = []
        for doc, vector in zip(documents, vectors, strict=True):
            embedding = [float(x) for x in vector.tolist()]
            self._update_dimension(embedding)
            embedded_docs.append(EmbeddedDocument(document=doc, embedding=embedding))
        return embedded_docs

    @staticmethod
    def _load_sentence_transformer(model_name: str) -> Any:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover - dependency error path
            raise InternalServerError(
                "sentence-transformers is not installed. Install dependencies before indexing."
            ) from exc

        try:
            return SentenceTransformer(model_name)
        except Exception as exc:  # pragma: no cover - model load path
            raise InternalServerError(f"Failed to load embedding model: {model_name}") from exc

    def _ensure_model_loaded(self) -> None:
        if self._settings.embedding_provider != "sentence_transformers":
            return
        if self._model is None:
            self._model = self._load_sentence_transformer(self._settings.embedding_model)

    def _build_embedding_input(self, doc: RagDocument) -> str:
        players = as_list(doc.metadata.get("players"))
        players_text = ", ".join(str(x) for x in players[:6]) if players else "n/a"
        return (
            f"Title: {safe_text(doc.title, 'n/a')}\n"
            f"Type: {doc.documentType}\n"
            f"Category: {safe_text(doc.category, 'n/a')}\n"
            f"Players: {players_text}\n"
            f"Text: {doc.text}"
        )

    def _update_dimension(self, vector: list[float]) -> None:
        dim = len(vector)
        if dim <= 0:
            raise InternalServerError("Generated invalid embedding with zero dimensions.")
        if self._embedding_dim is None:
            self._embedding_dim = dim
            return
        if self._embedding_dim != dim:
            raise InternalServerError(
                f"Embedding dimension mismatch: expected {self._embedding_dim}, got {dim}."
            )
