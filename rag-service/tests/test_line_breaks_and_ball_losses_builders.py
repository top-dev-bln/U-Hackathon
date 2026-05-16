from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.builders.attacking_patterns_builder import AttackingPatternsDocumentBuilder
from app.builders.ball_losses_builder import BallLossesDocumentBuilder
from app.builders.line_breaks_builder import LineBreaksDocumentBuilder


class NewInputBuildersTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.line_breaks_payload = json.loads((root / "input_line_breaks.json").read_text(encoding="utf-8"))
        self.ball_losses_payload = json.loads((root / "input_ball_losses.json").read_text(encoding="utf-8"))
        self.attacking_patterns_payload = json.loads(
            (root / "input_attacking_patterns.json").read_text(encoding="utf-8")
        )

    def test_line_breaks_builder_generates_documents(self) -> None:
        builder = LineBreaksDocumentBuilder()
        docs, warnings = builder.build(
            match_id=900000001,
            team_id=14,
            team_name="Universitatea Cluj",
            payload=self.line_breaks_payload,
        )

        self.assertGreaterEqual(len(docs), 1)
        doc_types = {doc.documentType for doc in docs}
        self.assertIn("line_breaks_summary", doc_types)
        self.assertIsInstance(warnings, list)

    def test_ball_losses_builder_generates_documents(self) -> None:
        builder = BallLossesDocumentBuilder()
        docs, warnings = builder.build(
            match_id=900000001,
            team_id=14,
            team_name="Universitatea Cluj",
            payload=self.ball_losses_payload,
        )

        self.assertGreaterEqual(len(docs), 1)
        doc_types = {doc.documentType for doc in docs}
        self.assertIn("ball_losses_summary", doc_types)
        self.assertIn("ball_loss_heatmap_summary", doc_types)
        self.assertIsInstance(warnings, list)

    def test_attacking_patterns_builder_generates_documents(self) -> None:
        builder = AttackingPatternsDocumentBuilder()
        docs, warnings = builder.build(
            match_id=900000001,
            team_id=14,
            team_name="Universitatea Cluj",
            payload=self.attacking_patterns_payload,
        )

        self.assertGreaterEqual(len(docs), 1)
        doc_types = {doc.documentType for doc in docs}
        self.assertIn("attacking_patterns_summary", doc_types)
        self.assertIsInstance(warnings, list)


if __name__ == "__main__":
    unittest.main()
