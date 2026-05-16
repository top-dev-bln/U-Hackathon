# Data Quality Report

## Snapshot
- Device session rows: 745
- Device rows with mapped wy_id: 745 (100.00%)
- Distinct device names: 26
- Unmatched device names: 0
- Daily rows in player_day_features: 645
- Distinct players in player_day_features: 26
- Date range in player_day_features: 2025-09-12 -> 2025-12-20

## Integrity Checks
- Duplicate keys on (wy_id, date): 0
- Device rows with missing parsed session_date: 100

## Outlier Scan (simple threshold q99*1.5)
- Distance daily q99: 10904.24, outliers: 0
- Duration daily q99: 126.18, outliers: 0

## Unmatched Names
- None

## Notes / Limitations
- Match JSON files do not contain explicit match date fields in this dataset.
- match_day_flag and days_since_match are placeholders until match dates are added.
- For this phase, match metrics are player-level season aggregates joined on wy_id.
