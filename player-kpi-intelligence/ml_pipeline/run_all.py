from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    PROJECT_ROOT / "ml_pipeline" / "build_dataset.py",
    PROJECT_ROOT / "ml_pipeline" / "build_features_v1.py",
    PROJECT_ROOT / "ml_pipeline" / "run_kpi_baseline.py",
]


def main() -> None:
    for script in SCRIPTS:
        print(f"\n=== running: {script.name} ===", flush=True)
        result = subprocess.run([sys.executable, str(script)], cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    print("\nPipeline completed successfully.", flush=True)


if __name__ == "__main__":
    main()
