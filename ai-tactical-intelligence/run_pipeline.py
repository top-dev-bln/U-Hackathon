from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from tactical_baseline.pipeline import run_pipeline  # noqa: E402


if __name__ == "__main__":
    artifacts = run_pipeline()
    print("Pipeline artifacts generated:")
    for key, path in artifacts.items():
        print(f"- {key}: {path}")
