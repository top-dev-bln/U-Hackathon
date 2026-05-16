# KPI Definition

Source table: `outputs/player_kpi_daily.csv`
Operational weekly table: `outputs/player_kpi_weekly.csv` (cadence 7 days).

## Core KPIs
- `form_score_7d`, `form_score_14d`: modelled form scores scaled 0-100 by role.
- `fatigue_risk_prob`: model risk probability (0-1).
- `fatigue_risk_level`: low/medium/high from risk probability thresholds.
- `overload_flag`: 1 when fatigue_risk_prob is in high zone.
- `ac_combined_status`: below_optimal / optimal / above_optimal from personalized A:C bands.
- `cluster_profile`: tactical/physical profile cluster label.

## Operational flags
- `underload_candidate`: below optimal AC with low fatigue risk.
- `overload_candidate`: high risk or AC above optimal zone.

## Ranking fields
- `rank_form_7d`: descending rank by form score inside same date.
- `rank_fatigue_risk`: descending rank by fatigue risk inside same date.
