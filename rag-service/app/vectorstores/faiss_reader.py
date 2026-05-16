from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from app.core.errors import InternalServerError, NotFoundError
from app.schemas.retrieval import RetrievedDocument


class FaissReader:
    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir
        self._cache: dict[str, tuple[Any, list[dict[str, Any]]]] = {}
        self._collection_re = re.compile(r"^[a-z0-9_]+$")

    def list_matches(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for path in self._storage_dir.glob("match_*"):
            if not path.is_dir():
                continue
            match_id = self._parse_match_id(path.name)
            if match_id is None:
                continue
            docs_path = path / "documents.json"
            count = 0
            if docs_path.exists():
                try:
                    with docs_path.open("r", encoding="utf-8") as f:
                        rows = json.load(f)
                    if isinstance(rows, list):
                        count = len(rows)
                except json.JSONDecodeError:
                    count = 0
            entries.append(
                {
                    "matchId": match_id,
                    "collectionName": path.name,
                    "documentsCount": count,
                    "vectorStore": "faiss",
                }
            )
        entries.sort(key=lambda item: item["matchId"])
        return entries

    def list_collections(self, *, prefix: str | None = None) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for path in self._storage_dir.iterdir():
            if not path.is_dir():
                continue
            collection_name = path.name
            if prefix and not collection_name.startswith(prefix):
                continue
            docs_path = path / "documents.json"
            count = 0
            if docs_path.exists():
                try:
                    with docs_path.open("r", encoding="utf-8") as f:
                        rows = json.load(f)
                    if isinstance(rows, list):
                        count = len(rows)
                except json.JSONDecodeError:
                    count = 0
            entries.append(
                {
                    "collectionName": collection_name,
                    "documentsCount": count,
                    "vectorStore": "faiss",
                }
            )
        entries.sort(key=lambda item: item["collectionName"])
        return entries

    def load_match_documents(self, match_id: int) -> list[dict[str, Any]]:
        _, rows = self._load_collection(f"match_{match_id}")
        return [{k: v for k, v in row.items() if k != "vectorId"} for row in rows]

    def load_collection_documents(self, collection_name: str) -> list[dict[str, Any]]:
        _, rows = self._load_collection(collection_name)
        return [{k: v for k, v in row.items() if k != "vectorId"} for row in rows]

    def search(
        self,
        *,
        match_id: int,
        query_vector: list[float],
        top_k: int,
        candidate_k: int | None = None,
    ) -> list[RetrievedDocument]:
        return self.search_collection(
            collection_name=f"match_{match_id}",
            query_vector=query_vector,
            top_k=top_k,
            candidate_k=candidate_k,
            source_scope="match",
        )

    def search_collection(
        self,
        *,
        collection_name: str,
        query_vector: list[float],
        top_k: int,
        candidate_k: int | None = None,
        source_scope: str,
    ) -> list[RetrievedDocument]:
        index, rows = self._load_collection(collection_name)
        if not rows:
            return []

        query_np = np.array([query_vector], dtype="float32")
        if query_np.ndim != 2 or query_np.shape[1] <= 0:
            raise InternalServerError("Invalid query embedding shape for FAISS search.")

        self._normalize(query_np)
        query_dim = int(query_np.shape[1])
        if int(index.d) != query_dim:
            raise InternalServerError(
                f"Query embedding dimension ({query_dim}) does not match index dimension ({index.d})."
            )

        k = candidate_k if candidate_k is not None else top_k
        k = max(top_k, k)
        max_k = min(max(k, top_k), len(rows))
        if max_k <= 0:
            return []

        scores, ids = index.search(query_np, max_k)
        results: list[RetrievedDocument] = []
        for idx, score in zip(ids[0].tolist(), scores[0].tolist(), strict=True):
            if idx < 0 or idx >= len(rows):
                continue
            payload = rows[idx]
            match_id_raw = payload.get("matchId")
            doc = RetrievedDocument(
                docId=str(payload.get("docId")),
                matchId=int(match_id_raw) if isinstance(match_id_raw, int) else None,
                teamId=payload.get("teamId"),
                teamName=payload.get("teamName"),
                sourceService=str(payload.get("sourceService")),
                sourceScope=source_scope,
                documentType=str(payload.get("documentType")),
                category=payload.get("category"),
                title=payload.get("title"),
                text=str(payload.get("text", "")),
                metadata=payload.get("metadata") or {},
                score=float(score),
            )
            results.append(doc)
        return results

    def clear_cache(self) -> None:
        self._cache.clear()

    def _load_collection(self, collection_name: str) -> tuple[Any, list[dict[str, Any]]]:
        normalized_name = self._normalize_collection_name(collection_name)
        cached = self._cache.get(normalized_name)
        if cached is not None:
            return cached

        collection_dir = self._storage_dir / normalized_name
        index_path = collection_dir / "index.faiss"
        docs_path = collection_dir / "documents.json"
        if not index_path.exists() or not docs_path.exists():
            raise NotFoundError(f"No FAISS index found for collection '{normalized_name}'.")

        try:
            import faiss
        except Exception as exc:  # pragma: no cover - dependency error path
            raise InternalServerError("faiss-cpu is not installed.") from exc

        try:
            index = faiss.read_index(str(index_path))
        except Exception as exc:
            raise InternalServerError(
                f"Failed to load FAISS index for collection '{normalized_name}'."
            ) from exc

        try:
            with docs_path.open("r", encoding="utf-8") as f:
                rows = json.load(f)
        except json.JSONDecodeError as exc:
            raise InternalServerError(
                f"Malformed documents.json for collection '{normalized_name}'."
            ) from exc

        if not isinstance(rows, list):
            raise InternalServerError(
                f"Expected list in documents.json for collection '{normalized_name}'."
            )

        cached_value = (index, rows)
        self._cache[normalized_name] = cached_value
        return cached_value

    @staticmethod
    def _parse_match_id(name: str) -> int | None:
        if not name.startswith("match_"):
            return None
        try:
            return int(name.replace("match_", "", 1))
        except ValueError:
            return None

    @staticmethod
    def _normalize(matrix: np.ndarray) -> None:
        try:
            import faiss
        except Exception as exc:  # pragma: no cover - dependency error path
            raise InternalServerError("faiss-cpu is not installed.") from exc
        faiss.normalize_L2(matrix)

    def _normalize_collection_name(self, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or self._collection_re.fullmatch(normalized) is None:
            raise InternalServerError(
                f"Invalid collection name '{value}'. Use lowercase letters, numbers, underscore."
            )
        return normalized
