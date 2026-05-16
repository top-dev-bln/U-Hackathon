# ML Pipeline (Baseline v1)

## Run all stages

```bash
python ml_pipeline/run_all.py
```

## Run stage by stage

```bash
python ml_pipeline/build_dataset.py
python ml_pipeline/build_features_v1.py
python ml_pipeline/run_kpi_baseline.py
```

## Stage outputs

- `data/player_day_features.csv`
- `data/name_mapping_review.csv`
- `data_quality_report.md`
- `features/features_v1.csv`
- `features_dictionary.md`
- `outputs/form_scores_daily.csv`
- `outputs/fatigue_alerts_daily.csv`
- `outputs/ac_ratio_daily.csv`
- `outputs/player_specific_ac_thresholds.csv`
- `outputs/player_clusters.csv`
- `outputs/player_kpi_daily.csv`
- `outputs/player_kpi_weekly.csv`
- `reports/baseline_results.md`
- `reports/backtest_v1.csv`
- `reports/form_model_eval.md`
- `reports/fatigue_model_eval.md`
- `reports/ac_personalization.md`
- `reports/clustering_profile_book.md`
- `models/form_7d.pkl`
- `models/form_14d.pkl`
- `models/fatigue_risk.pkl`
- `kpi_definition.md`
- `targets/targets_v1.csv`
- `target_definition.md`

## FastAPI endpoint

Install dependencies:

```bash
pip install -r requirements.txt
```

Run API:

```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Get all players data:

```bash
GET /players
```

## Manual mapping override

If you need to force a device name to a player id:

1. Open `config/manual_name_overrides.json`.
2. Add mapping in normalized format:

```json
{
  "raji": 123456
}
```

3. Re-run:

```bash
python ml_pipeline/run_all.py
```

## Notes

- Current dataset does not include explicit match dates in match JSON files.
- `match_day_flag` and `days_since_match` are placeholders until match dates are available.
