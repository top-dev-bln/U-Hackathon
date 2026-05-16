from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional import path
    load_dotenv = None

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DOTENV_PATH = _PROJECT_ROOT / ".env"
if load_dotenv is not None and _DOTENV_PATH.exists():
    load_dotenv(dotenv_path=_DOTENV_PATH, override=False)


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_name: str
    vector_store: str
    storage_dir: Path
    embedding_provider: str
    embedding_model: str
    max_phase_documents: int
    max_player_documents: int
    rag_top_k_default: int
    rag_top_k_max: int
    rag_context_max_chars: int
    rag_history_max_messages: int
    rag_history_message_max_chars: int
    rag_min_score_default: float
    rag_llm_provider: str
    rag_openai_model: str
    rag_openai_reasoning_effort: str
    rag_openai_timeout_sec: int
    openai_api_key: str | None
    debug: bool


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {name}: {value}") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be > 0, got {parsed}")
    return parsed


def _read_float(name: str, default: float) -> float:
    value = os.getenv(name, str(default))
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid float value for {name}: {value}") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "dev")
    storage_dir = Path(os.getenv("STORAGE_DIR", "./storage/vector_store")).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        app_env=app_env,
        app_name="tactical-rag-service",
        vector_store=os.getenv("VECTOR_STORE", "faiss").lower(),
        storage_dir=storage_dir,
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").lower(),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        max_phase_documents=_read_int("MAX_PHASE_DOCUMENTS", 10),
        max_player_documents=_read_int("MAX_PLAYER_DOCUMENTS", 10),
        rag_top_k_default=_read_int("RAG_TOP_K_DEFAULT", 4),
        rag_top_k_max=_read_int("RAG_TOP_K_MAX", 20),
        rag_context_max_chars=_read_int("RAG_CONTEXT_MAX_CHARS", 5000),
        rag_history_max_messages=_read_int("RAG_HISTORY_MAX_MESSAGES", 5),
        rag_history_message_max_chars=_read_int("RAG_HISTORY_MESSAGE_MAX_CHARS", 800),
        rag_min_score_default=_read_float("RAG_MIN_SCORE_DEFAULT", -1.0),
        rag_llm_provider=os.getenv("RAG_LLM_PROVIDER", "openai").lower(),
        rag_openai_model=os.getenv("RAG_OPENAI_MODEL", "gpt-5-mini"),
        rag_openai_reasoning_effort=os.getenv("RAG_OPENAI_REASONING_EFFORT", "low").lower(),
        rag_openai_timeout_sec=_read_int("RAG_OPENAI_TIMEOUT_SEC", 20),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        debug=app_env != "prod",
    )
