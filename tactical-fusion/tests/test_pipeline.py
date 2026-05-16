from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tactical_fusion.ingestion import ValidationError, load_json_file
from tactical_fusion.pipeline import run_fusion


class FusionPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parent.parent
        cls.input1 = load_json_file(root / "input1.json")
        cls.input2 = load_json_file(root / "input2.json")

    def test_end_to_end_output_shape(self) -> None:
        result = run_fusion(self.input1, self.input2)
        self.assertIn("fusionOutput", result)
        self.assertIn("frontendOutput", result)

        fusion_output = result["fusionOutput"]
        self.assertIn("combinedInsights", fusion_output)
        self.assertIn("playerPriorities", fusion_output)
        self.assertIn("trainingFocus", fusion_output)
        self.assertGreater(len(fusion_output["combinedInsights"]), 0)

    def test_deterministic_output_for_same_input(self) -> None:
        first = run_fusion(self.input1, self.input2)
        second = run_fusion(self.input1, self.input2)
        self.assertEqual(first, second)

    def test_validation_error_on_missing_required_field(self) -> None:
        invalid = copy.deepcopy(self.input1)
        del invalid["baselineModel"]
        with self.assertRaises(ValidationError):
            run_fusion(invalid, self.input2)


if __name__ == "__main__":
    unittest.main()
