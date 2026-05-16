from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from app.core.errors import InternalServerError
from app.services.embedding_service import EmbeddedDocument


class FaissStore:
    _COLLECTION_RE = re.compile(r"^[a-z0-9_]+$")

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def save_match_index(
        self,
        *,
        match_id: int,
        embedded_documents: list[EmbeddedDocument],
        rebuild: bool,
    ) -> None:
        self.save_collection_index(
            collection_name=f"match_{match_id}",
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
        if not embedded_documents:
            raise InternalServerError("Cannot save FAISS index: no embedded documents.")

        collection_dir = self._collection_dir(collection_name)
        if collection_dir.exists():
            if not rebuild:
                raise InternalServerError(
                    f"Index for collection '{collection_name}' already exists and rebuild=false."
                )
            shutil.rmtree(collection_dir)
        collection_dir.mkdir(parents=True, exist_ok=True)

        vectors = np.array([item.embedding for item in embedded_documents], dtype="float32")
        if vectors.ndim != 2 or vectors.shape[0] == 0 or vectors.shape[1] == 0:
            raise InternalServerError("Invalid vectors matrix for FAISS save.")

        try:
            import faiss
        except Exception as exc:  # pragma: no cover - dependency error path
            raise InternalServerError("faiss-cpu is not installed.") from exc

        try:
            faiss.normalize_L2(vectors)
            index = faiss.IndexFlatIP(int(vectors.shape[1]))
            index.add(vectors)
            faiss.write_index(index, str(collection_dir / "index.faiss"))
        except Exception as exc:
            raise InternalServerError(
                f"Failed to save FAISS index for collection '{collection_name}'."
            ) from exc

        serialized_docs: list[dict[str, Any]] = []
        for i, item in enumerate(embedded_documents):
            row = item.document.model_dump()
            row["vectorId"] = i
            serialized_docs.append(row)
        with (collection_dir / "documents.json").open("w", encoding="utf-8") as f:
            json.dump(serialized_docs, f, ensure_ascii=False, indent=2)

    def load_match_documents(self, match_id: int) -> list[dict[str, Any]]:
        return self.load_collection_documents(collection_name=f"match_{match_id}")

    def load_collection_documents(self, *, collection_name: str) -> list[dict[str, Any]]:
        path = self._collection_dir(collection_name) / "documents.json"
        if not path.exists():
            raise FileNotFoundError(f"No documents found for collection '{collection_name}'.")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise InternalServerError(f"documents.json malformed for collection '{collection_name}'.")
        return data

    def list_indexes(self) -> list[dict[str, Any]]:
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
                        content = json.load(f)
                    if isinstance(content, list):
                        count = len(content)
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

    def delete_match_index(self, match_id: int) -> bool:
        path = self._collection_dir(f"match_{match_id}")
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True

    def delete_collection_index(self, *, collection_name: str) -> bool:
        path = self._collection_dir(collection_name)
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True

    def _match_dir(self, match_id: int) -> Path:
        return self._storage_dir / f"match_{match_id}"

    def _collection_dir(self, collection_name: str) -> Path:
        name = collection_name.strip().lower()
        if not name or not self._COLLECTION_RE.fullmatch(name):
            raise InternalServerError(
                f"Invalid collection name '{collection_name}'. Use lowercase letters, numbers, underscore."
            )
        return self._storage_dir / name

    @staticmethod
    def _parse_match_id(name: str) -> int | None:
        if not name.startswith("match_"):
            return None
        raw = name.replace("match_", "", 1)
        try:
            return int(raw)
        except ValueError:
            return None
