from __future__ import annotations

import unittest
from dataclasses import replace

from app.core.config import get_settings
from app.schemas.retrieval import RetrievedDocument
from app.services.llm_service import LlmService
from app.services.query_service import QueryService


class QueryAnswerFallbackAndCitationTests(unittest.TestCase):
    def test_openai_missing_key_uses_fallback(self) -> None:
        settings = replace(get_settings(), rag_llm_provider="openai", openai_api_key=None)
        service = LlmService(settings)
        source = RetrievedDocument(
            docId="match_1_sample",
            matchId=1,
            teamId=14,
            teamName="U Cluj",
            sourceService="tactical-baseline-service",
            sourceScope="match",
            documentType="baseline_summary",
            category="baseline",
            title="Baseline",
            text="Risk and weakness detected in build-up shape.",
            metadata={"page": 9},
            score=0.42,
        )

        answer, model, warnings = service.answer(
            question="Care sunt riscurile?",
            context="Question: Care sunt riscurile?\nEvidence documents:\n...",
            sources=[source],
        )

        self.assertEqual(model, "fallback-template")
        self.assertTrue(any("OPENAI_API_KEY missing" in warning for warning in warnings))
        self.assertIn("Observatii:", answer)
        self.assertIn("Riscuri:", answer)
        self.assertIn("Actiuni recomandate:", answer)

    def test_query_service_appends_source_citations_line(self) -> None:
        source_a = RetrievedDocument(
            docId="match_1_baseline",
            matchId=1,
            teamId=14,
            teamName="U Cluj",
            sourceService="tactical-baseline-service",
            sourceScope="match",
            documentType="baseline_summary",
            category="baseline",
            title="Baseline summary",
            text="Sample text.",
            metadata={"page": 11},
            score=0.9,
        )
        source_b = RetrievedDocument(
            docId="u_cluj_tactical_principle_build_up",
            matchId=None,
            teamId=14,
            teamName="U Cluj",
            sourceService="club-knowledge-pdf-service",
            sourceScope="club",
            documentType="tactical_principle",
            category="build_up",
            title="Build-up principle",
            text="Sample text.",
            metadata={"pages": [3, 4]},
            score=0.8,
        )

        base_answer = "Observatii:\n- Test.\n\nRiscuri:\n- Test.\n\nActiuni recomandate:\n- Test."
        result = QueryService._append_source_citations(base_answer, [source_a, source_b])

        self.assertIn("Surse utilizate:", result)
        self.assertIn("match_1_baseline", result)
        self.assertIn("u_cluj_tactical_principle_build_up", result)
        self.assertIn("p.11", result)
        self.assertIn("p.3", result)


if __name__ == "__main__":
    unittest.main()
