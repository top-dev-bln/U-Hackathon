from __future__ import annotations

from app.core.config import Settings
from app.schemas.query import ChatHistoryMessage
from app.schemas.retrieval import RetrievedDocument
from app.utils.text_formatting import safe_text


class ContextService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_context(
        self,
        *,
        session_id: str,
        question: str,
        retrieved: list[RetrievedDocument],
        chat_history: list[ChatHistoryMessage] | None = None,
        context_max_chars: int | None = None,
    ) -> tuple[str, list[RetrievedDocument], list[str]]:
        warnings: list[str] = []
        if not retrieved:
            return "", [], ["No retrieved documents available for context."]

        budget = context_max_chars or self._settings.rag_context_max_chars
        if budget < 1000:
            budget = 1000

        ordered = sorted(retrieved, key=lambda item: item.score, reverse=True)
        picked: list[RetrievedDocument] = []
        chunks: list[str] = []
        current_len = 0

        intro = (
            f"Session ID:\n{session_id}\n\n"
            "Question:\n"
            f"{question}\n\n"
        )
        if chat_history:
            intro += self._render_chat_history(chat_history) + "\n"
        intro += "Evidence documents:\n"
        current_len += len(intro)

        for doc in ordered:
            block = self._render_doc_block(doc)
            if current_len + len(block) > budget:
                continue
            chunks.append(block)
            picked.append(doc)
            current_len += len(block)

        if not picked:
            warnings.append("Context budget too small; including top-1 doc only.")
            top = ordered[0]
            chunks = [self._render_doc_block(top)]
            picked = [top]

        context = intro + "".join(chunks)
        return context, picked, warnings

    @staticmethod
    def _render_doc_block(doc: RetrievedDocument) -> str:
        players = doc.metadata.get("players") if isinstance(doc.metadata, dict) else None
        players_text = ", ".join(str(x) for x in players[:4]) if isinstance(players, list) else "n/a"
        text = doc.text.strip().replace("\n", " ")
        if len(text) > 360:
            text = text[:360].rstrip() + "..."
        return (
            f"[docId={doc.docId} | scope={doc.sourceScope} | type={doc.documentType} | score={doc.score:.4f}]\n"
            f"title: {safe_text(doc.title, 'n/a')}\n"
            f"category: {safe_text(doc.category, 'n/a')}\n"
            f"players: {players_text}\n"
            f"text: {text}\n\n"
        )

    @staticmethod
    def _render_chat_history(chat_history: list[ChatHistoryMessage]) -> str:
        lines = ["Recent conversation (last 5 messages):"]
        for msg in chat_history:
            role = msg.role.upper()
            text = msg.text.replace("\n", " ").strip()
            if len(text) > 180:
                text = text[:180].rstrip() + "..."
            lines.append(f"- {role}: {text}")
        return "\n".join(lines)
