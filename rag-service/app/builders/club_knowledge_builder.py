from __future__ import annotations

from typing import Any

from app.builders.common import make_doc
from app.schemas.documents import RagDocument
from app.utils.ids import slugify
from app.utils.text_formatting import safe_text


class ClubKnowledgeDocumentBuilder:
    source_service = "club-knowledge-pdf-service"

    _PHILOSOPHY_KEYWORDS = (
        "filozofie",
        "philosophy",
        "identitate",
        "identity",
        "adn",
        "model de joc",
        "style of play",
        "principii",
        "principles",
    )

    _PHASE_KEYWORDS: dict[str, tuple[str, ...]] = {
        "build_up": ("build up", "constructie", "progressie", "progresie", "first line"),
        "pressing": ("pressing", "counter-press", "gegenpress", "agresivitate"),
        "transition": ("tranzitie", "transition", "ball loss", "ball win"),
        "final_third": ("final third", "treimea ofensiva", "last third", "zona 14"),
        "defense": ("defense", "defensiv", "organizare defensiva", "compact"),
    }

    _PRINCIPLE_KEYWORDS: dict[str, tuple[str, ...]] = {
        "build_up": ("superioritate", "breaking first line", "depth", "width"),
        "ball_loss": ("ball loss", "pierderea mingii", "safety pass", "rest defense"),
        "pressing": ("pressing", "timing", "agresivitate", "trigger"),
        "transition": ("tranzitie", "counter", "recuperare", "reaction"),
        "final_third": ("final third", "finalizare", "shot", "chance creation"),
    }

    _PLAYER_ROLE_KEYWORDS = (
        "profil jucator",
        "player profile",
        "rol",
        "role",
        "pozitie",
        "position",
    )

    def build(
        self,
        *,
        club_key: str,
        team_id: int | None,
        team_name: str | None,
        pages: list[dict[str, Any]],
        max_chars_per_page: int,
    ) -> tuple[list[RagDocument], list[str]]:
        warnings: list[str] = []
        docs: list[RagDocument] = []
        safe_club_key = slugify(club_key)
        normalized_pages = self._normalize_pages(pages=pages, max_chars_per_page=max_chars_per_page)
        if not normalized_pages:
            return [], ["No extractable text pages from PDF."]

        overview_text, overview_pages = self._build_overview_text(normalized_pages)
        docs.append(
            make_doc(
                doc_id=f"{safe_club_key}_club_philosophy_overview",
                match_id=None,
                team_id=team_id,
                team_name=team_name,
                source_service=self.source_service,
                document_type="club_philosophy",
                title=f"{safe_text(team_name, club_key)} philosophy overview",
                category="club_knowledge",
                text=overview_text,
                metadata={
                    "source": "pdf",
                    "section": "philosophy_overview",
                    "pages": overview_pages,
                    "clubKey": safe_club_key,
                    "tags": ["club_knowledge", "philosophy"],
                },
            )
        )

        for phase, keywords in self._PHASE_KEYWORDS.items():
            phase_text, phase_pages = self._build_topic_text(
                pages=normalized_pages,
                keywords=keywords,
                fallback_pages=2,
            )
            if not phase_text:
                continue
            docs.append(
                make_doc(
                    doc_id=f"{safe_club_key}_game_phase_{phase}",
                    match_id=None,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="game_phase",
                    title=f"Game phase: {phase}",
                    category=phase,
                    text=phase_text,
                    metadata={
                        "source": "pdf",
                        "section": "game_phase",
                        "phase": phase,
                        "pages": phase_pages,
                        "clubKey": safe_club_key,
                        "tags": ["club_knowledge", "game_phase", phase],
                    },
                )
            )

        for principle, keywords in self._PRINCIPLE_KEYWORDS.items():
            principle_text, principle_pages = self._build_topic_text(
                pages=normalized_pages,
                keywords=keywords,
                fallback_pages=0,
            )
            if not principle_text:
                warnings.append(f"No principle text found for category '{principle}'.")
                continue
            docs.append(
                make_doc(
                    doc_id=f"{safe_club_key}_tactical_principle_{principle}",
                    match_id=None,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="tactical_principle",
                    title=f"Tactical principle: {principle}",
                    category=principle,
                    text=principle_text,
                    metadata={
                        "source": "pdf",
                        "section": "tactical_principle",
                        "principle": principle,
                        "pages": principle_pages,
                        "clubKey": safe_club_key,
                        "tags": ["club_knowledge", "tactical_principle", principle],
                    },
                )
            )

        role_candidates = self._find_pages_by_keywords(normalized_pages, self._PLAYER_ROLE_KEYWORDS, limit=4)
        for idx, row in enumerate(role_candidates, start=1):
            page = row["page"]
            text = row["text"]
            docs.append(
                make_doc(
                    doc_id=f"{safe_club_key}_player_role_profile_{idx}",
                    match_id=None,
                    team_id=team_id,
                    team_name=team_name,
                    source_service=self.source_service,
                    document_type="player_role_profile",
                    title=f"Player role profile p.{page}",
                    category="player_profile",
                    text=text,
                    metadata={
                        "source": "pdf",
                        "section": "player_role_profile",
                        "page": page,
                        "pages": [page],
                        "clubKey": safe_club_key,
                        "tags": ["club_knowledge", "player_role_profile"],
                    },
                )
            )

        if not role_candidates:
            warnings.append("No player role profile sections found in PDF text.")

        return docs, warnings

    @staticmethod
    def _normalize_pages(*, pages: list[dict[str, Any]], max_chars_per_page: int) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in pages:
            page = row.get("page")
            text = str(row.get("text", "")).replace("\n", " ").strip()
            text = " ".join(text.split())
            if not text:
                continue
            if len(text) > max_chars_per_page:
                text = text[:max_chars_per_page].rstrip() + "..."
            normalized.append({"page": int(page), "text": text})
        return normalized

    def _build_overview_text(self, pages: list[dict[str, Any]]) -> tuple[str, list[int]]:
        selected = self._find_pages_by_keywords(pages, self._PHILOSOPHY_KEYWORDS, limit=4)
        if not selected:
            selected = pages[:2]
        text = " ".join(item["text"] for item in selected).strip()
        page_numbers = sorted({int(item["page"]) for item in selected})
        return text, page_numbers

    def _build_topic_text(
        self,
        *,
        pages: list[dict[str, Any]],
        keywords: tuple[str, ...],
        fallback_pages: int,
    ) -> tuple[str, list[int]]:
        selected = self._find_pages_by_keywords(pages, keywords, limit=4)
        if not selected and fallback_pages > 0:
            selected = pages[:fallback_pages]
        if not selected:
            return "", []
        text = " ".join(item["text"] for item in selected).strip()
        page_numbers = sorted({int(item["page"]) for item in selected})
        return text, page_numbers

    @staticmethod
    def _find_pages_by_keywords(
        pages: list[dict[str, Any]],
        keywords: tuple[str, ...],
        limit: int,
    ) -> list[dict[str, Any]]:
        scored: list[tuple[int, dict[str, Any]]] = []
        lowered_keywords = tuple(k.lower() for k in keywords)
        for row in pages:
            text = str(row["text"]).lower()
            score = sum(1 for key in lowered_keywords if key in text)
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[: max(1, limit)]]
