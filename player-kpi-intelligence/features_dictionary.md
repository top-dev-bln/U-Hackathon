# Features Dictionary

Output: `features/features_v1.csv`

## Core inputs
- Daily load/device metrics from `data/player_day_features.csv`.
- Player-level match context columns prefixed with `match_`.

## Rolling features
- For each base metric, generated for windows: 3d, 7d, 14d, 21d, 28d.
- Suffixes:
- `_sum_<wd>` cumulative value over window.
- `_mean_<wd>` arithmetic mean over window.
- `_std_<wd>` population std over window.
- `_cv_<wd>` coefficient of variation (std/mean).

## Derived training load features
- `monotony_7d`, `monotony_14d` = load mean / load std.
- `strain_7d`, `strain_14d` = load sum * monotony.
- `training_load_week_over_week_delta`, `training_load_week_over_week_ratio`.

## Acute:Chronic ratios
- `ac_distance_3_21`, `ac_distance_7_21`, `ac_distance_7_28`.
- `ac_high_int_3_21`, `ac_high_int_7_21`, `ac_high_int_7_28`.
- `ac_load_3_21`, `ac_load_7_21`, `ac_load_7_28`.
- EWMA ratios: `ac_distance_ewma_7_28`, `ac_high_int_ewma_7_28`, `ac_load_ewma_7_28`.

## Smoothing / personalization
- EWMA for selected metrics: `_ewma_7d`, `_ewma_28d`.
- Player personalized z-score: `*_zscore_player` (expanding history, no future leakage).
- Baseline ratio: `*_ratio_vs_baseline`.

## Notes
- `features_v1` is stored as CSV for portability in current environment.
- Match day flags remain placeholders until explicit match dates are added to source data.
