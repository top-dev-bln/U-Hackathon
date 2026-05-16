from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock

from app.schemas.query import ChatHistoryMessage


class ChatHistoryService:
    def __init__(self, *, max_messages: int = 5, max_message_chars: int = 800) -> None:
        self._max_messages = max(1, int(max_messages))
        self._max_message_chars = max(80, int(max_message_chars))
        self._store: dict[str, deque[ChatHistoryMessage]] = {}
        self._lock = Lock()

    def get_recent(self, session_id: str) -> list[ChatHistoryMessage]:
        with self._lock:
            messages = self._store.get(session_id)
            if messages is None:
                return []
            return list(messages)

    def append_user(self, session_id: str, text: str) -> None:
        self._append(session_id=session_id, role="user", text=text)

    def append_assistant(self, session_id: str, text: str) -> None:
        self._append(session_id=session_id, role="assistant", text=text)

    def clear(self, session_id: str) -> int:
        with self._lock:
            existing = self._store.pop(session_id, None)
            return len(existing) if existing is not None else 0

    def _append(self, *, session_id: str, role: str, text: str) -> None:
        clipped = " ".join(text.split()).strip()
        if len(clipped) > self._max_message_chars:
            clipped = clipped[: self._max_message_chars].rstrip() + "..."
        message = ChatHistoryMessage(
            role=role,
            text=clipped,
            timestamp=datetime.now(timezone.utc),
        )
        with self._lock:
            queue = self._store.get(session_id)
            if queue is None:
                queue = deque(maxlen=self._max_messages)
                self._store[session_id] = queue
            queue.append(message)

