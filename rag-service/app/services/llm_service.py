from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.errors import InternalServerError
from app.schemas.retrieval import RetrievedDocument


class LlmService:
    _INLINE_REF_RE = re.compile(r"\s*\[match_[^\]]+\]")
    _SPACES_RE = re.compile(r"[ \t]{2,}")

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._openai_client: Any | None = None
        self._system_prompt = self._load_prompt()

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    def answer(
        self,
        *,
        question: str,
        context: str,
        sources: list[RetrievedDocument],
    ) -> tuple[str, str, list[str]]:
        warnings: list[str] = []
        if not context.strip() or not sources:
            return (
                "Observatii:\n- Evidence insuficient pentru intrebare.\n\n"
                "Riscuri:\n- Nu pot evalua sigur fara documente relevante.\n\n"
                "Actiuni recomandate:\n- Ruleaza query cu topK mai mare sau fara filtre stricte.",
                "no-model",
                ["Insufficient context for LLM answer generation."],
            )

        if self._settings.rag_llm_provider == "openai":
            answer = self._answer_openai(question=question, context=context, warnings=warnings)
            if answer is not None:
                cleaned = self._strip_inline_references(answer)
                return self._enforce_bullet_limit(cleaned, max_bullets=7), self._settings.rag_openai_model, warnings
            warnings.append("OpenAI answer failed, used deterministic fallback.")

        fallback = self._fallback_answer(question=question, sources=sources)
        cleaned_fallback = self._strip_inline_references(fallback)
        return self._enforce_bullet_limit(cleaned_fallback, max_bullets=7), "fallback-template", warnings

    def _answer_openai(self, *, question: str, context: str, warnings: list[str]) -> str | None:
        if not self._settings.openai_api_key:
            warnings.append("OPENAI_API_KEY missing; skipping OpenAI call.")
            return None

        try:
            client = self._get_openai_client()
            user_prompt = (
                f"Question:\n{question}\n\n"
                f"Context:\n{context}\n\n"
                "Return Romanian response following the specified format. "
                "Keep total bullets between 5 and 7."
            )
            input_payload = [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": self._system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ]

            request_kwargs: dict[str, Any] = {
                "model": self._settings.rag_openai_model,
                "input": input_payload,
                "timeout": self._settings.rag_openai_timeout_sec,
            }
            reasoning_cfg = self._build_reasoning_config()
            if reasoning_cfg is not None:
                request_kwargs["reasoning"] = reasoning_cfg

            try:
                response = client.responses.create(**request_kwargs)
            except Exception:
                if reasoning_cfg is None:
                    raise
                # Retry once without reasoning for compatibility and lower latency.
                warnings.append("Reasoning config failed; retried without reasoning.")
                response = client.responses.create(
                    model=self._settings.rag_openai_model,
                    input=input_payload,
                    timeout=self._settings.rag_openai_timeout_sec,
                )
            text = getattr(response, "output_text", None)
            if isinstance(text, str) and text.strip():
                return text.strip()
            fallback = self._extract_output_text(response)
            if fallback:
                return fallback
            warnings.append("OpenAI response had no text output.")
            return None
        except Exception as exc:
            warnings.append(f"OpenAI call failed: {exc}")
            return None

    def _build_reasoning_config(self) -> dict[str, Any] | None:
        effort = (self._settings.rag_openai_reasoning_effort or "").strip().lower()
        if effort in {"", "none", "off", "disabled"}:
            return None
        return {"effort": effort}

    def _get_openai_client(self) -> Any:
        if self._openai_client is not None:
            return self._openai_client
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - dependency path
            raise InternalServerError("openai package is not installed.") from exc
        self._openai_client = OpenAI(
            api_key=self._settings.openai_api_key,
            max_retries=0,
            timeout=self._settings.rag_openai_timeout_sec,
        )
        return self._openai_client

    @staticmethod
    def _extract_output_text(response: Any) -> str | None:
        output = getattr(response, "output", None)
        if output is None and hasattr(response, "to_dict"):
            try:
                output = response.to_dict().get("output")
            except Exception:
                output = None
        if not isinstance(output, list):
            return None
        pieces: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if content is None and isinstance(item, dict):
                content = item.get("content")
            if isinstance(content, list):
                for block in content:
                    text = getattr(block, "text", None)
                    if text is None and isinstance(block, dict):
                        text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        pieces.append(text.strip())
            # Some SDK payloads may expose `output_text` directly per item.
            item_text = getattr(item, "output_text", None)
            if item_text is None and isinstance(item, dict):
                item_text = item.get("output_text")
            if isinstance(item_text, str) and item_text.strip():
                pieces.append(item_text.strip())
        if not pieces:
            return None
        return "\n".join(pieces)

    @staticmethod
    def _enforce_bullet_limit(text: str, max_bullets: int) -> str:
        lines = text.splitlines()
        kept: list[str] = []
        bullets = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("-"):
                if bullets >= max_bullets:
                    continue
                bullets += 1
            kept.append(line)
        # Remove empty trailing sections if bullets were trimmed heavily.
        while kept and not kept[-1].strip():
            kept.pop()
        return "\n".join(kept).strip()

    @staticmethod
    def _fallback_answer(*, question: str, sources: list[RetrievedDocument]) -> str:
        top = sources[:5]
        obs = []
        risks = []
        actions = []
        for doc in top[:2]:
            snippet = doc.text.strip().replace("\n", " ")
            if len(snippet) > 120:
                snippet = snippet[:120].rstrip() + "..."
            obs.append(f"- {snippet}")
        for doc in top:
            lowered = doc.text.lower()
            if len(risks) < 2 and ("critical" in lowered or "risk" in lowered or "weakness" in lowered):
                risks.append(f"- Risc identificat in {doc.documentType}.")
            if len(actions) < 2 and ("recommend" in lowered or "training" in lowered or "focus" in lowered):
                actions.append(f"- Aplica recomandarea din {doc.documentType}.")
        if len(obs) < 2:
            obs.append("- Dovezi insuficiente pentru observatii detaliate.")
        if not risks:
            risks = ["- Riscuri explicite insuficiente in contextul curent."]
        if not actions:
            actions = ["- Ruleaza query cu topK mai mare pentru recomandari mai clare."]
        return (
            "Observatii:\n"
            f"- Intrebare: {question}\n"
            + "\n".join(obs[:2])
            + "\n\nRiscuri:\n"
            + "\n".join(risks[:2])
            + "\n\nActiuni recomandate:\n"
            + "\n".join(actions[:2])
        )

    @classmethod
    def _strip_inline_references(cls, text: str) -> str:
        cleaned = cls._INLINE_REF_RE.sub("", text)
        lines = cleaned.splitlines()
        normalized_lines = [cls._SPACES_RE.sub(" ", line).rstrip() for line in lines]
        return "\n".join(normalized_lines).strip()

    @staticmethod
    def _load_prompt() -> str:
        path = Path(__file__).resolve().parents[1] / "prompts" / "answer_prompt.txt"
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise InternalServerError(f"Prompt file missing: {path}") from exc
