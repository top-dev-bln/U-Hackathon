# Tactical Fusion Dataset (Starter)

This folder contains a starter dataset for calibration.

## Included now
- `manifest.csv`: sample registry and train/val/test split.
- `labels.jsonl`: one JSON object per sample with supervision labels.
- `samples/*.json`: raw `input1` and `input2` payloads.

## Important
- Current labels are `weak_labeled` bootstrap labels.
- Before real calibration, replace `label_quality=weak` with analyst-reviewed labels.

## Add a new sample
1. Copy raw files into `samples/` using:
   - `<date>_<team>_input1.json`
   - `<date>_<team>_input2.json`
2. Add one row in `manifest.csv`.
3. Add one line in `labels.jsonl` with same `sample_id`.
