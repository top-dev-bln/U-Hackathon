# Target Definition (Provisional v1)

Target dataset: `targets/targets_v1.csv`

## Form Targets
- `target_form_proxy_7d`: media `form_proxy_current` in urmatoarele 7 zile.
- `target_form_proxy_14d`: media `form_proxy_current` in urmatoarele 14 zile.
- `form_proxy_current` = `0.50*distance_per_min + 0.25*high_speed_share_pct + 2*power_metabolic_avg_wkg + 20*sprints_count_per_min`.

## Fatigue / Overload Proxy Targets
- `fatigue_proxy_binary`: 1 cand modelul baseline marcheaza nivel `high`.
- `overload_proxy_binary`: 1 cand `overload_flag` este activ.

## Important
- Aceste target-uri sunt provizorii si trebuie confirmate/calibrate cu staff-ul tehnic.
