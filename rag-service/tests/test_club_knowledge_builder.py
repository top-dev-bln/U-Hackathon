from __future__ import annotations

import unittest

from app.builders.club_knowledge_builder import ClubKnowledgeDocumentBuilder


class ClubKnowledgeBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = ClubKnowledgeDocumentBuilder()

    def test_build_generates_expected_document_types_and_metadata(self) -> None:
        pages = [
            {
                "page": 1,
                "text": (
                    "Filozofie identitate si ADN, model de joc, style of play si principles."
                ),
            },
            {
                "page": 2,
                "text": (
                    "Constructie build up cu superioritate, depth, width si breaking first line."
                ),
            },
            {
                "page": 3,
                "text": (
                    "Pressing cu agresivitate, timing si trigger in tranzitie dupa ball loss."
                ),
            },
            {
                "page": 4,
                "text": (
                    "Player profile si rol pe pozitie. Role interpretation pentru midfielder."
                ),
            },
        ]

        docs, warnings = self.builder.build(
            club_key="u_cluj",
            team_id=14,
            team_name="Universitatea Cluj",
            pages=pages,
            max_chars_per_page=2000,
        )

        self.assertGreaterEqual(len(docs), 4)
        types = {doc.documentType for doc in docs}
        self.assertIn("club_philosophy", types)
        self.assertIn("game_phase", types)
        self.assertIn("tactical_principle", types)
        self.assertIn("player_role_profile", types)

        doc_ids = {doc.docId for doc in docs}
        self.assertIn("u_cluj_club_philosophy_overview", doc_ids)
        self.assertTrue(any(doc_id.startswith("u_cluj_tactical_principle_") for doc_id in doc_ids))

        for doc in docs:
            self.assertEqual(doc.metadata.get("source"), "pdf")
            self.assertEqual(doc.metadata.get("clubKey"), "u_cluj")
            self.assertIsInstance(doc.metadata.get("pages"), list)

        self.assertIsInstance(warnings, list)

    def test_build_returns_warning_for_empty_pages(self) -> None:
        docs, warnings = self.builder.build(
            club_key="u_cluj",
            team_id=14,
            team_name="Universitatea Cluj",
            pages=[],
            max_chars_per_page=2000,
        )
        self.assertEqual(docs, [])
        self.assertIn("No extractable text pages from PDF.", warnings)


if __name__ == "__main__":
    unittest.main()
