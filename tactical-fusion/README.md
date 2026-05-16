# Tactical Fusion API

Tactical Fusion is a Python service that combines:
- Tactical Baseline input (`input1`)
- Decision Quality input (`input2`)

It returns actionable tactical outputs:
- combined insights
- player priorities
- training focus
- frontend-ready summary

This repo is currently configured for hackathon usage with mock data support.

## Features
- FastAPI service with Swagger docs
- Two explicit request modes:
  - `POST /fusion/analysis/json`
  - `POST /fusion/analysis/multipart`
- Legacy compatibility endpoint:
  - `POST /fusion/analysis` (hidden from Swagger)
- Synthetic dataset generator (50-100+ matches)
- Calibration pipeline (weights + severity thresholds)
- Unit/integration tests

## Project Structure
```text
tactical_fusion/
  api/
  fusion/
  ingestion/
  insights/
  normalization/
  calibration_config.json
scripts/
  generate_mock_dataset.py
  calibrate_fusion.py
dataset/
  mock_100/
tests/
run_fusion.py
run_fusion_api.py
```

## Quick Start

### 1) Create and activate virtual environment (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies
```powershell
python -m pip install -r requirements.txt
```

### 3) Run API
```powershell
python run_fusion_api.py
```

Open Swagger:
- `http://127.0.0.1:8080/docs`

## API Usage

### Health
- `GET /health`

### JSON body mode
- `POST /fusion/analysis/json`
```json
{
  "input1": { "...": "tactical baseline payload" },
  "input2": { "...": "decision quality payload" }
}
```

### Multipart mode
- `POST /fusion/analysis/multipart`
- form-data fields:
  - `input1` -> `.json` file
  - `input2` -> `.json` file

Example:
```bash
curl -X POST "http://127.0.0.1:8080/fusion/analysis/multipart" \
  -F "input1=@input1.json;type=application/json" \
  -F "input2=@input2.json;type=application/json"
```

## Offline Run
Run fusion directly without API:
```powershell
python run_fusion.py --input1 input1.json --input2 input2.json --output fusion_output.json
```

Use calibrated config:
```powershell
python run_fusion.py --config tactical_fusion\calibration_config.json --output fusion_output_calibrated.json
```

## Mock Data + Calibration

Generate mock dataset:
```powershell
python scripts\generate_mock_dataset.py --matches 100 --seed 42 --out-dir dataset\mock_100
```

Run calibration:
```powershell
python scripts\calibrate_fusion.py --dataset-dir dataset\mock_100 --output dataset\mock_100\calibration_result.json --export-config tactical_fusion\calibration_config.json
```

## Tests
```powershell
python -m unittest discover -s tests -v
```

## Notes
- Current calibration config is tuned on synthetic data (`dataset/mock_100`).
- For production use, recalibrate with analyst-labeled real match data.
