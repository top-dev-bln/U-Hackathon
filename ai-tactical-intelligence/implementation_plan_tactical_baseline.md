# Implementation Plan - Tactical Baseline (Wyscout `*_players_stats.json`)

## 1. Scope si obiectiv

Construim un pipeline end-to-end care:

1. Incarca toate fisierele `*_players_stats.json` din `Date - meciuri`.
2. Produce dataset-uri player-level si team-match-level.
3. Calculeaza metrici derivate + baseline de liga.
4. Compara meciurile U Cluj cu baseline-ul.
5. Genereaza insights rule-based + anomaly score + tactical profile.
6. Exporta artefactele finale (`csv`/`json`) pentru integrare backend/frontend.

Snapshot curent date (24 Apr 2026): `278` fisiere `*_players_stats.json`.

---

## 2. Structura propusa in repo

```text
PythonProject2/
  Date - meciuri/
  src/
    tactical_baseline/
      __init__.py
      config.py
      io_loader.py
      flatten_players.py
      team_aggregate.py
      feature_engineering.py
      baseline.py
      comparator.py
      insights.py
      anomaly.py
      clustering.py
      report_builder.py
      pipeline.py
  outputs/
    player_level_dataset.csv
    team_match_dataset.csv
    league_baseline.json
    league_distributions.json
    u_cluj_match_comparisons.json
    u_cluj_tactical_weakness_report.json
    tactical_clusters.json
    anomaly_scores.csv
  implementation_plan_tactical_baseline.md
```

---

## 3. Milestones + status

Legenda status: `[ ] TODO`, `[-] IN PROGRESS`, `[x] DONE`, `[!] BLOCKED`

### M0 - Project bootstrap

- [x] Creeaza pachetul `src/tactical_baseline`.
- [x] Definește config central (paths, naming, coloane mandatory).
- [x] Creeaza `outputs/` si un entrypoint (`pipeline.py` + `run_pipeline.py`).
- [x] Setup dependinte minime: `pandas`, `numpy`, `scikit-learn`.
- [x] Adauga logging standard (INFO/WARNING/ERROR).

Acceptance criteria:

- Ruleaza entrypoint fara crash si afiseaza config-ul activ.

### M1 - Data ingestion (`*_players_stats.json`)

- [x] Loader care citeste recursiv fisierele dupa pattern `*_players_stats.json`.
- [x] Exclude explicit fisiere auxiliare (ex: `players (1).json`).
- [x] Validari schema minime (`players` list, `matchId` existent).
- [x] Raport de calitate date (fisiere citite, erori, meciuri unice).

Acceptance criteria:

- Produce `load_report.json` cu total fisiere, parse errors, unique matchIds.

### M2 - Flatten player-level dataset

- [x] Extrage campuri common (`playerId`, `matchId`, `competitionId`, `seasonId`, `roundId`, positions).
- [x] Flatten pentru `total.*`, `average.*`, `percent.*`.
- [x] Filtru `minutesOnField > 0` (cand exista campul).
- [x] Normalizeaza tipuri numerice (`float`/`int`) + `NaN` handling.

Acceptance criteria:

- Export `player_level_dataset.csv` + verificari de consistenta (randuri > 0, matchId populat).

### M3 - Team-match aggregation

- [x] Mapping robust player -> team in each match (din campuri existente in stats; fallback config daca lipseste).
- [x] Agregare pe `(matchId, teamId)` pentru metricile brute din roadmap.
- [x] Validare: fiecare match are maxim 2 echipe (cu exceptii logate).

Acceptance criteria:

- Export `team_match_dataset.csv` cu chei unice `(matchId, teamId)`.

### M4 - Feature engineering

- [x] Calculeaza metricile derivate (pass/loss/shot/pressing/duel rates).
- [x] Safe division helper (default `0` la denominator `0`).
- [x] Marcheaza metric direction (`higher_is_better` vs `higher_is_worse`).

Acceptance criteria:

- Dataset team-match include toate metricile cheie fara crash la impartiri.

### M5 - League baseline + distributions

- [x] Pentru fiecare metrica: `mean/std/min/max/p10/p25/p50/p75/p90`.
- [x] Persista `league_baseline.json` + `league_distributions.json`.
- [x] Adauga verificari simple de sanity (std >= 0, percentile ordonate).

Acceptance criteria:

- Fisierele baseline sunt generate si citibile JSON-valid.

### M6 - U Cluj comparator

- [x] Detecteaza meciurile U Cluj (config cu alias-uri nume echipa).
- [x] Calculeaza `zScore`, `percentile`, `status` contextual pe directia metricii.
- [x] Export `u_cluj_match_comparisons.json`.

Acceptance criteria:

- Pentru fiecare meci U Cluj exista comparatie completa pe metricile principale.

### M7 - Rule-based insight engine

- [x] Reguli pentru: build-up, ball loss, final third, pressing, duels.
- [x] Scor severitate + confidence + evidence + recommendation.
- [x] Ranking + limitare la max 6 insights/meci.

Acceptance criteria:

- Export `u_cluj_tactical_weakness_report.json` cu insight-uri explicabile.

### M8 - Anomaly detection (IsolationForest)

- [x] Fit pe team-match rows (feature set definit in config).
- [x] Score + predict pentru meciurile U Cluj.
- [x] Export `anomaly_scores.csv`.

Acceptance criteria:

- Fiecare meci U Cluj are `anomalyScore` si `isAnomalous`.

### M9 - Tactical clustering (KMeans)

- [x] Fit KMeans (`k=4`/`k=5`, alegere justificata).
- [x] Etichetare semantica a clusterelor dupa medii.
- [x] Export `tactical_clusters.json`.

Acceptance criteria:

- Fiecare meci are `clusterId` + `tacticalProfile`.

### M10 - Final report builder

- [x] Compune payload final pe meci (comparisons + insights + anomaly + cluster).
- [x] Calculeaza `overallWeaknessScore` (ponderi roadmap).
- [x] Export final per meci U Cluj.

Acceptance criteria:

- JSON final valid pentru consum backend/frontend.

### M11 - Validare minima (fara test suite)

- [x] Smoke run end-to-end pe toate fisierele.
- [x] Validare automata: `matchId` prezent pentru toate randurile relevante.
- [x] Validare automata: cheie unica `(matchId, teamId)` in team-match dataset.
- [x] Validare automata: fara `NaN/inf` in metricile derivate critice.
- [x] Genereaza `sanity_report.json` (numar fisiere, meciuri, randuri, metrice lipsa).

Acceptance criteria:

- Pipeline complet ruleaza end-to-end fara erori si produce raport de sanity.

---

## 4. Ordinea de executie (next actions)

1. Implementam `M0` si `M1`.
2. Validam ingestia pe toate fisierele reale.
3. Continuam cu `M2` + `M3` (dataset-uri intermediare stabile).
4. Abia dupa ce datele sunt corecte, activam `M4`-`M10`.
5. Inchidem cu `M11` (smoke run + sanity checks).

---

## 5. Assumptions / clarificari deschise

- [ ] Confirmam sursa `teamId` daca lipseste in unele player stats.
- [ ] Confirmam alias-uri U Cluj (ex: `Universitatea Cluj`, `U Cluj`).
- [ ] Confirmam daca tratam sezon multiplu intr-un singur baseline sau separat.
- [ ] Confirmam daca mentinem `safe division = 0` in toate metricile.

---

## 6. Progress log

### 2026-04-24

- [x] Roadmap actualizat la naming real `*_players_stats.json`.
- [x] Verificare dataset: `278` fisiere stats valide, `278` `matchId` unice.
- [x] Planul de implementare creat (acest fisier).
- [x] Implementat `M0` (bootstrap, config, logging, entrypoint, requirements).
- [x] Implementat `M1` (loader + validari + `outputs/load_report.json`).
- [x] Implementat `M2` (flatten + `outputs/player_level_dataset.csv` + `outputs/player_level_report.json`).
- [x] Implementat `M3` (team aggregation + `outputs/team_match_dataset.csv` + `outputs/team_match_report.json`).
- [x] Implementat `M4` (feature engineering + `outputs/team_match_features_dataset.csv` + `outputs/team_match_features_report.json` + `outputs/metric_directions.json`).
- [x] Implementat `M5` (baseline + distributions + `outputs/league_baseline.json` + `outputs/league_distributions.json`).
- [x] Implementat `M6` (U Cluj comparator + `outputs/u_cluj_match_comparisons.json`).
- [x] Implementat `M7` (rule-based insights + `outputs/u_cluj_tactical_weakness_report.json`).
- [x] Implementat `M8` (IsolationForest + `outputs/anomaly_scores.csv` + `outputs/anomaly_report.json`).
- [x] Implementat `M9` (KMeans + `outputs/tactical_clusters.json` + `outputs/tactical_clusters_report.json`).
- [x] Implementat `M10` (final report builder + `outputs/u_cluj_tactical_weakness_report.json`).
- [x] Implementat `M11` (validare minima + `outputs/sanity_report.json`).
- [x] Pipeline roadmap M0-M11 complet.
- [!] Nota calitate M3: 640 randuri au fost asignate prin `match_balance_fallback` deoarece input-ul nu contine `teamId` per player.
- [x] Sensitivity check strict vs heuristic implementat (`outputs/team_match_dataset_heuristic.csv`, `outputs/team_match_dataset_strict.csv`, `outputs/team_assignment_sensitivity_report.json`).
- [x] Decizie blocata in config: `team_assignment_mode = strict`.
- [x] M4 sanity: `rows_with_nonfinite_values = 0`; safe division activ (ex: `pressingDuelSuccessRate` cu `denominator=0` in 53 randuri).
- [x] M6 output: `35` meciuri U Cluj detectate; comparatii complete pe `19` metrici.
- [x] M7 sanity: max `6` insights/meci respectat; `35` meciuri analizate (`2` fara insights).
- [x] M8 output: `556` rows scorate, `35` rows U Cluj scorate, `6` meciuri U Cluj marcate anormale.
- [x] M9 output: `k=5`, toate `556` row-uri clusterizate; distributia U Cluj pe clustere disponibila in report.
- [x] M10 output: raport final U Cluj complet cu `overallWeaknessScore`, `riskLevel`, `tacticalProfile`, `anomalyScore`, `comparisons`, `insights`.
- [x] M11 output: `sanity_report.json` cu status `passed` si 5/5 verificari trecute.
