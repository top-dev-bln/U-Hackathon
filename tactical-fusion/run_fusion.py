from __future__ import annotations

import argparse
import json
from pathlib import Path

from tactical_fusion.ingestion import load_json_file
from tactical_fusion.pipeline import run_fusion


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run tactical fusion for one input pair.")
    parser.add_argument("--input1", default="input1.json", help="Path to Tactical Baseline input JSON.")
    parser.add_argument("--input2", default="input2.json", help="Path to Decision Quality input JSON.")
    parser.add_argument(
        "--config",
        default=None,
        help="Optional calibration config JSON path.",
    )
    parser.add_argument(
        "--output",
        default="fusion_output.json",
        help="Output file path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    input1 = load_json_file(root / args.input1)
    input2 = load_json_file(root / args.input2)
    calibration = load_json_file(root / args.config) if args.config else None
    result = run_fusion(input1, input2, calibration_config=calibration)

    output_path = root / args.output
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Fusion output written to: {output_path}")


if __name__ == "__main__":
    main()
