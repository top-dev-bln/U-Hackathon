from __future__ import annotations

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.schemas.retrieval import RetrievedDocument
from app.utils.ids import slugify
from app.vectorstores.faiss_reader import FaissReader


class RetrievalService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._reader = FaissReader(settings.storage_dir)

    def retrieve(
        self,
        *,
        match_id: int,
        query_vector: list[float],
        top_k: int,
        club_key: str | None = None,
        include_club_knowledge: bool = False,
        team_id: int | None = None,
        document_types: list[str] | None = None,
        min_score: float | None = None,
    ) -> tuple[list[RetrievedDocument], list[str]]:
        warnings: list[str] = []
        normalized_doc_types = {x.lower() for x in (document_types or [])}
        threshold = self._settings.rag_min_score_default if min_score is None else float(min_score)
        safe_top_k = max(1, min(top_k, self._settings.rag_top_k_max))
        candidate_k = min(max(safe_top_k * 5, safe_top_k), self._settings.rag_top_k_max * 10)

        match_candidates = self._reader.search(
            match_id=match_id,
            query_vector=query_vector,
            top_k=safe_top_k,
            candidate_k=candidate_k,
        )
        filtered_match = self._apply_filters(
            docs=match_candidates,
            team_id=team_id,
            doc_types=normalized_doc_types,
            min_score=threshold,
        )
        filtered_club: list[RetrievedDocument] = []
        merged_docs = list(filtered_match)

        if include_club_knowledge:
            if club_key is None:
                warnings.append("includeClubKnowledge=true but no clubKey provided; skipped club retrieval.")
            else:
                collection_name = f"club_knowledge_{slugify(club_key)}"
                try:
                    club_candidates = self._reader.search_collection(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        top_k=safe_top_k,
                        candidate_k=candidate_k,
                        source_scope="club",
                    )
                    filtered_club = self._apply_filters(
                        docs=club_candidates,
                        team_id=team_id,
                        doc_types=normalized_doc_types,
                        min_score=threshold,
                    )
                    merged_docs = self._blend_results(
                        match_docs=filtered_match,
                        club_docs=filtered_club,
                        top_k=safe_top_k,
                    )
                except NotFoundError:
                    warnings.append(
                        f"Club knowledge collection not found: {collection_name}. "
                        "Continue with match-only retrieval."
                    )

        if not merged_docs and (team_id is not None or normalized_doc_types or min_score is not None):
            warnings.append("No results after filters. Retrying with relaxed filters.")
            filtered_match = self._apply_filters(
                docs=match_candidates,
                team_id=None,
                doc_types=set(),
                min_score=self._settings.rag_min_score_default,
            )
            merged_docs = list(filtered_match)
            if include_club_knowledge and club_key is not None:
                collection_name = f"club_knowledge_{slugify(club_key)}"
                try:
                    club_candidates = self._reader.search_collection(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        top_k=safe_top_k,
                        candidate_k=candidate_k,
                        source_scope="club",
                    )
                    filtered_club = self._apply_filters(
                        docs=club_candidates,
                        team_id=None,
                        doc_types=set(),
                        min_score=self._settings.rag_min_score_default,
                    )
                    merged_docs = self._blend_results(
                        match_docs=filtered_match,
                        club_docs=filtered_club,
                        top_k=safe_top_k,
                    )
                except NotFoundError:
                    pass

        merged_docs.sort(key=lambda item: item.score, reverse=True)
        deduped = self._dedupe_by_doc_id(merged_docs)
        return deduped[:safe_top_k], warnings

    def list_matches(self) -> list[dict]:
        return self._reader.list_matches()

    def list_club_collections(self) -> list[dict]:
        return self._reader.list_collections(prefix="club_knowledge_")

    def list_sources(self, match_id: int, limit: int = 100) -> list[RetrievedDocument]:
        rows = self._reader.load_match_documents(match_id)
        docs = [
            RetrievedDocument(
                docId=str(row.get("docId")),
                matchId=row.get("matchId"),
                teamId=row.get("teamId"),
                teamName=row.get("teamName"),
                sourceService=str(row.get("sourceService")),
                sourceScope="match",
                documentType=str(row.get("documentType")),
                category=row.get("category"),
                title=row.get("title"),
                text=str(row.get("text", "")),
                metadata=row.get("metadata") or {},
                score=0.0,
            )
            for row in rows[: max(1, limit)]
        ]
        return docs

    def list_club_sources(self, club_key: str, limit: int = 100) -> list[RetrievedDocument]:
        collection_name = f"club_knowledge_{slugify(club_key)}"
        rows = self._reader.load_collection_documents(collection_name)
        docs = [
            RetrievedDocument(
                docId=str(row.get("docId")),
                matchId=row.get("matchId"),
                teamId=row.get("teamId"),
                teamName=row.get("teamName"),
                sourceService=str(row.get("sourceService")),
                sourceScope="club",
                documentType=str(row.get("documentType")),
                category=row.get("category"),
                title=row.get("title"),
                text=str(row.get("text", "")),
                metadata=row.get("metadata") or {},
                score=0.0,
            )
            for row in rows[: max(1, limit)]
        ]
        return docs

    @staticmethod
    def _apply_filters(
        *,
        docs: list[RetrievedDocument],
        team_id: int | None,
        doc_types: set[str],
        min_score: float,
    ) -> list[RetrievedDocument]:
        filtered: list[RetrievedDocument] = []
        for doc in docs:
            if team_id is not None and doc.teamId is not None and int(doc.teamId) != int(team_id):
                continue
            if doc_types and doc.documentType.lower() not in doc_types:
                continue
            if doc.score < min_score:
                continue
            filtered.append(doc)
        filtered.sort(key=lambda item: item.score, reverse=True)
        return filtered

    @staticmethod
    def _dedupe_by_doc_id(docs: list[RetrievedDocument]) -> list[RetrievedDocument]:
        seen: set[str] = set()
        result: list[RetrievedDocument] = []
        for doc in docs:
            if doc.docId in seen:
                continue
            seen.add(doc.docId)
            result.append(doc)
        return result

    @classmethod
    def _blend_results(
        cls,
        *,
        match_docs: list[RetrievedDocument],
        club_docs: list[RetrievedDocument],
        top_k: int,
    ) -> list[RetrievedDocument]:
        if not club_docs:
            return list(match_docs)
        if not match_docs:
            return list(club_docs)

        target_match = max(1, top_k // 2)
        target_club = max(1, top_k - target_match)
        picked = match_docs[:target_match] + club_docs[:target_club]

        if len(picked) < top_k:
            remainder = cls._dedupe_by_doc_id(match_docs[target_match:] + club_docs[target_club:])
            picked.extend(remainder[: max(0, top_k - len(picked))])
        return cls._dedupe_by_doc_id(picked)
