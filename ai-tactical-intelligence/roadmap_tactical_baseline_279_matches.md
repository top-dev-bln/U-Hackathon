# Roadmap - Tactical Baseline Model pe fisiere Wyscout *_players_stats.json

## 1. Obiectiv

Construim un model / engine care invata "normalul" din Superliga folosind toate meciurile reale Wyscout disponibile in fisierele `*_players_stats.json`.

Scopul nu este sa prezicem scorul sau castigatorul.

Scopul este sa putem raspunde la intrebarea:

```text
Cum arata performanta unei echipe intr-un meci fata de media ligii?
```

Apoi folosim acest engine pentru U Cluj:

```text
U Cluj match stats
        ↓
comparatie cu baseline Superliga
        ↓
detectare slabiciuni tactice
        ↓
insights explicabile
```

---

## 2. Ce date folosim

Input principal:

```text
players_stats.json
```

Avem aproximativ:

```text
toate meciurile reale Wyscout disponibile
snapshot curent in `Date - meciuri`: 278 fisiere `*_players_stats.json`
```

Aceste fisiere contin statistici agregate pe jucator si meci.

Structura generala:

```json
{
  "players": [
    {
      "playerId": 123,
      "matchId": 5715833,
      "competitionId": 719,
      "seasonId": 191642,
      "roundId": 4435361,
      "positions": [],
      "total": {},
      "average": {},
      "percent": {}
    }
  ]
}
```

Important:

```text
players_stats.json NU contine evenimente individuale.
Nu avem minut, coordonate, faze, pase concrete sau alternative reale.
```

Deci folosim aceste date pentru:

```text
baseline
comparatii
anomaly detection
tactical profiles
weakness detection la nivel de echipa / meci
```

Nu pentru:

```text
event-level decision quality
passing network real
heatmap real pe coordonate
pass vs shot vs carry la minut concret
```

---

## 3. Input-ul modelului

### 3.1 Input la training / fit

Modelul primeste toate fisierele care respecta pattern-ul `*_players_stats.json`.

Input brut:

```text
folder/
  Arges - Botosani, 0-0_players_stats.json
  Arges - Dinamo Bucuresti, 1-1_5715786_players_stats.json
  CFR Cluj - FCS Bucuresti, 2-2_players_stats.json
  ...
  UTA Arad - Universitatea Craiova, 3-3_players_stats.json
```

Regula de selectie input:

```text
include doar fisierele cu sufixul exact *_players_stats.json
nu include fisiere auxiliare (ex: players (1).json)
```

Din fiecare fisier extragem:

```text
playerId
matchId
teamId daca exista
competitionId
seasonId
roundId
positions
total.*
average.*
percent.*
```

Daca in players_stats nu exista explicit `teamId`, trebuie facut join cu alt fisier Wyscout, de exemplu:

```text
matches.json
teams.json
players.json
```

sau un mapping intern:

```text
playerId -> teamId pentru acel match
```

Fara teamId putem calcula doar player-level, nu team-level corect.

---

### 3.2 Input la predict / analiza U Cluj

Pentru a analiza un meci U Cluj, engine-ul primeste:

```text
players_stats.json pentru meciul U Cluj
teamScope = FC Universitatea Cluj
```

Optional, mai tarziu:

```text
decision_quality_output.json
```

Dar pentru acest roadmap ne bazam prima data DOAR pe meciurile din fisierele `*_players_stats.json`.

---

## 4. Output-ul final dorit

Pentru un meci U Cluj, output-ul final ar trebui sa fie:

```json
{
  "matchId": 5715833,
  "teamId": 9001,
  "teamName": "FC Universitatea Cluj",
  "baselineScope": "Superliga - all available matches",
  "overallWeaknessScore": 0.68,
  "tacticalProfile": "low_progression_high_losses",
  "anomalyScore": 0.73,
  "metrics": {},
  "comparisons": {},
  "insights": []
}
```

Exemplu complet:

```json
{
  "matchId": 5715833,
  "teamName": "FC Universitatea Cluj",
  "overallWeaknessScore": 0.68,
  "tacticalProfile": "low_progression_high_losses",
  "anomalyScore": 0.73,
  "metrics": {
    "passSuccessRate": 0.74,
    "progressivePassSuccessRate": 0.48,
    "lossRate": 0.22,
    "xgPerShot": 0.08,
    "counterpressingRate": 0.18
  },
  "comparisons": {
    "progressivePassSuccessRate": {
      "value": 0.48,
      "leagueAverage": 0.61,
      "percentile": 18,
      "zScore": -1.55,
      "status": "weak"
    },
    "lossRate": {
      "value": 0.22,
      "leagueAverage": 0.17,
      "percentile": 78,
      "zScore": 1.32,
      "status": "warning"
    }
  },
  "insights": [
    {
      "type": "build_up",
      "severity": "high",
      "title": "Low build-up progression",
      "message": "U Cluj completed progressive passes below the Superliga baseline.",
      "evidence": {
        "value": 0.48,
        "leagueAverage": 0.61,
        "zScore": -1.55
      },
      "recommendation": "Improve central progression and third-man passing options."
    }
  ]
}
```

---

## 5. Etapa 1 - Parsare fisiere

### Obiectiv

Citire automata a tuturor fisierelor `*_players_stats.json` si transformare intr-un tabel.

### Input

```text
players_stats.json
```

### Output

Un dataframe player-level:

```text
player_id
match_id
team_id
position_code
minutes_on_field
passes
successful_passes
progressive_passes
successful_progressive_passes
losses
own_half_losses
dangerous_own_half_losses
shots
shots_on_target
xg_shot
xg_assist
recoveries
counterpressing_recoveries
duels
duels_won
...
```

### Observatie

Daca un jucator are `minutesOnField = 0`, de obicei il excludem din calculele de echipa.

Regula:

```text
pastreaza doar players cu minutesOnField > 0
```

---

## 6. Etapa 2 - Agregare la nivel de echipa-meci

### Obiectiv

Transformam datele player-level in date team-match-level.

Un rand devine:

```text
un meci + o echipa
```

Exemplu:

```text
matchId = 5715833
teamId = 9001
teamName = FC Universitatea Cluj
```

### Agregari

Pentru fiecare echipa din fiecare meci calculam sume:

```text
passes = sum(player.total.passes)
successfulPasses = sum(player.total.successfulPasses)
progressivePasses = sum(player.total.progressivePasses)
successfulProgressivePasses = sum(player.total.successfulProgressivePasses)
passesToFinalThird = sum(player.total.passesToFinalThird)
successfulPassesToFinalThird = sum(player.total.successfulPassesToFinalThird)
losses = sum(player.total.losses)
ownHalfLosses = sum(player.total.ownHalfLosses)
dangerousOwnHalfLosses = sum(player.total.dangerousOwnHalfLosses)
shots = sum(player.total.shots)
shotsOnTarget = sum(player.total.shotsOnTarget)
xgShot = sum(player.total.xgShot)
xgAssist = sum(player.total.xgAssist)
touchInBox = sum(player.total.touchInBox)
recoveries = sum(player.total.recoveries)
opponentHalfRecoveries = sum(player.total.opponentHalfRecoveries)
counterpressingRecoveries = sum(player.total.counterpressingRecoveries)
duels = sum(player.total.duels)
duelsWon = sum(player.total.duelsWon)
```

Output:

```text
team_match_dataset.csv
```

---

## 7. Etapa 3 - Metrici derivate

### Obiectiv

Cream feature-uri mai bune decat valorile brute.

### Metrici principale

```text
passSuccessRate = successfulPasses / passes
progressivePassSuccessRate = successfulProgressivePasses / progressivePasses
finalThirdPassSuccessRate = successfulPassesToFinalThird / passesToFinalThird
forwardPassSuccessRate = successfulForwardPasses / forwardPasses
lossRate = losses / (passes + dribbles + receivedPass)
ownHalfLossRate = ownHalfLosses / losses
dangerousLossRate = dangerousOwnHalfLosses / losses
shotOnTargetRate = shotsOnTarget / shots
xgPerShot = xgShot / shots
boxEfficiency = xgShot / touchInBox
counterpressingRate = counterpressingRecoveries / recoveries
highRecoveryRate = opponentHalfRecoveries / recoveries
duelSuccessRate = duelsWon / duels
defensiveDuelSuccessRate = defensiveDuelsWon / defensiveDuels
offensiveDuelSuccessRate = offensiveDuelsWon / offensiveDuels
```

### Safe division

Pentru impartiri la 0:

```text
daca denominator = 0:
  return 0
```

sau:

```text
return null si ignora la baseline
```

Pentru hackathon e mai simplu:

```text
return 0
```

---

## 8. Etapa 4 - Baseline Superliga

### Obiectiv

Invatam valorile normale din toate meciurile disponibile in `*_players_stats.json`.

Pentru fiecare metric calculam:

```text
mean
std
min
max
p10
p25
p50
p75
p90
```

Output:

```text
league_baseline.json
```

Exemplu:

```json
{
  "passSuccessRate": {
    "mean": 0.81,
    "std": 0.06,
    "p25": 0.77,
    "p50": 0.82,
    "p75": 0.86
  },
  "progressivePassSuccessRate": {
    "mean": 0.61,
    "std": 0.08,
    "p25": 0.55,
    "p50": 0.61,
    "p75": 0.67
  }
}
```

---

## 9. Etapa 5 - Comparatie cu baseline

### Obiectiv

Pentru fiecare meci U Cluj calculam cat de departe este fata de media ligii.

### Z-score

Formula:

```text
zScore = (value - leagueMean) / leagueStd
```

Interpretare:

```text
zScore < -1.5 = mult sub medie
zScore intre -1.5 si -0.75 = sub medie
zScore intre -0.75 si 0.75 = normal
zScore intre 0.75 si 1.5 = peste medie
zScore > 1.5 = mult peste medie
```

Atentie:

Pentru unele metrici, valoare mare = bine.

Exemple:

```text
passSuccessRate mare = bine
progressivePassSuccessRate mare = bine
xgPerShot mare = bine
counterpressingRate mare = bine
duelSuccessRate mare = bine
```

Pentru altele, valoare mare = rau.

Exemple:

```text
lossRate mare = rau
ownHalfLossRate mare = rau
dangerousLossRate mare = rau
```

Deci status-ul trebuie interpretat in functie de directia metricii.

---

## 10. Etapa 6 - Percentile

### Obiectiv

Pe langa z-score, calculam si percentila.

Exemplu:

```text
progressivePassSuccessRate percentile = 18
```

Interpretare:

```text
U Cluj este mai buna decat 18% dintre echipele din dataset la acest indicator.
Deci este in bottom 25%.
```

Reguli:

```text
percentile < 25 pentru metrici pozitive => weakness
percentile > 75 pentru metrici negative => weakness
```

---

## 11. Etapa 7 - Rule-based weakness detector

### Obiectiv

Transformam comparatiile in insight-uri.

### 11.1 Build-up weakness

Input:

```text
progressivePassSuccessRate
finalThirdPassSuccessRate
forwardPassSuccessRate
progressivePasses / passes
```

Reguli:

```text
daca progressivePassSuccessRate zScore < -1.0:
  insight = Low progressive pass success

daca finalThirdPassSuccessRate zScore < -1.0:
  insight = Low success entering final third

daca progressivePasses / passes este sub p25:
  insight = Low vertical progression
```

---

### 11.2 Ball loss weakness

Input:

```text
lossRate
ownHalfLossRate
dangerousLossRate
dangerousOwnHalfLosses
```

Reguli:

```text
daca lossRate percentile > 75:
  insight = High ball losses

daca ownHalfLossRate percentile > 75:
  insight = Risky losses in own half

daca dangerousOwnHalfLosses > 0 si dangerousLossRate peste medie:
  insight = Dangerous own-half losses
```

---

### 11.3 Final third weakness

Input:

```text
shots
shotsOnTarget
shotOnTargetRate
xgShot
xgPerShot
xgAssist
touchInBox
```

Reguli:

```text
daca shots mare, dar xgPerShot mic:
  insight = Low-quality shots

daca touchInBox mare, dar xgShot mic:
  insight = Poor box efficiency

daca xgAssist mic:
  insight = Low chance creation
```

---

### 11.4 Pressing weakness

Input:

```text
recoveries
opponentHalfRecoveries
counterpressingRecoveries
pressingDuels
pressingDuelsWon
```

Reguli:

```text
daca counterpressingRate sub p25:
  insight = Low counterpressing impact

daca highRecoveryRate sub p25:
  insight = Few high recoveries

daca pressingDuelSuccessRate sub p25:
  insight = Low pressing duel success
```

---

### 11.5 Duel weakness

Input:

```text
duels
duelsWon
defensiveDuels
defensiveDuelsWon
offensiveDuels
offensiveDuelsWon
aerialDuels
aerialDuelsWon
```

Reguli:

```text
daca duelSuccessRate sub p25:
  insight = Low duel success

daca defensiveDuelSuccessRate sub p25:
  insight = Defensive duel weakness

daca aerialDuelSuccessRate sub p25:
  insight = Aerial duel weakness
```

---

### 11.6 Player-level weakness

Input player-level:

```text
player losses
player ownHalfLosses
player passes
player successfulPasses
player progressivePasses
player xgShot
player touchInBox
player receivedPass
player position
```

Reguli:

```text
daca CF are receivedPass mic, shots mic, touchInBox mic:
  insight = Striker isolated

daca fundas are ownHalfLosses mare:
  insight = Risky build-up from defensive line

daca mijlocas are progressivePasses mic:
  insight = Low midfield progression

daca winger are crosses multe, successfulCrosses mici:
  insight = Low crossing efficiency
```

---

## 12. Etapa 8 - Anomaly Detection

### Obiectiv

Detectam daca un meci are profil tactic neobisnuit fata de restul ligii.

### Model recomandat

```text
IsolationForest
```

### Input features

```text
passSuccessRate
progressivePassSuccessRate
finalThirdPassSuccessRate
lossRate
ownHalfLossRate
dangerousLossRate
shotOnTargetRate
xgPerShot
boxEfficiency
counterpressingRate
highRecoveryRate
duelSuccessRate
```

### Training / fit

```text
fit pe toate team-match rows din fisierele `*_players_stats.json`
```

### Predict pentru U Cluj

```text
anomalyScore = model.score_samples(U Cluj match)
isAnomalous = model.predict(U Cluj match)
```

Output:

```json
{
  "anomalyScore": 0.73,
  "isAnomalous": true,
  "message": "This match profile is tactically unusual compared to the Superliga baseline."
}
```

---

## 13. Etapa 9 - Tactical Clustering

### Obiectiv

Grupam meciurile in profile tactice.

### Model recomandat

```text
KMeans
```

### Numar de clustere

Inceput:

```text
k = 4 sau k = 5
```

### Input features

Aceeasi lista ca la IsolationForest.

### Exemple de clustere

```text
Cluster 0: balanced_control
Cluster 1: high_loss_low_progression
Cluster 2: strong_pressing
Cluster 3: low_chance_creation
Cluster 4: direct_attacking
```

### Cum denumim clusterele

Dupa antrenare, calculam media metricilor pe cluster.

Exemplu:

```text
daca cluster are:
  lossRate mare
  progressivePassSuccessRate mic

nume:
  high_loss_low_progression
```

Output:

```json
{
  "tacticalProfile": "high_loss_low_progression",
  "clusterId": 1,
  "clusterExplanation": [
    "higher than average ball losses",
    "lower than average progressive passing success"
  ]
}
```

---

## 14. Etapa 10 - Overall Weakness Score

### Obiectiv

Un scor general 0-1 pentru cat de problematic a fost meciul.

Formula simpla:

```text
overallWeaknessScore =
  0.30 * buildUpWeaknessScore
+ 0.25 * ballLossWeaknessScore
+ 0.20 * finalThirdWeaknessScore
+ 0.15 * pressingWeaknessScore
+ 0.10 * duelWeaknessScore
```

Fiecare subscore este intre 0 si 1.

Exemplu:

```text
buildUpWeaknessScore = cat de mult sub baseline este progresia
ballLossWeaknessScore = cat de mult peste baseline sunt pierderile
finalThirdWeaknessScore = cat de slaba este calitatea sanselor
```

Output:

```json
{
  "overallWeaknessScore": 0.68,
  "riskLevel": "medium-high"
}
```

---

## 15. Etapa 11 - Insight ranking

### Obiectiv

Nu afisam 30 de insight-uri. Afisam cele mai importante 3-6.

Fiecare insight are:

```text
severityScore
confidence
evidence
recommendation
```

Sortare:

```text
severityScore desc
```

Limitare:

```text
max 6 insights
```

---

## 16. Format final insight

```json
{
  "type": "build_up",
  "severity": "high",
  "severityScore": 0.82,
  "title": "Low build-up progression",
  "message": "U Cluj completed progressive passes below the Superliga baseline.",
  "evidence": {
    "metric": "progressivePassSuccessRate",
    "value": 0.48,
    "leagueAverage": 0.61,
    "percentile": 18,
    "zScore": -1.55
  },
  "recommendation": "Improve central progression and third-man passing options."
}
```

---

## 17. Output-uri salvate

Dupa procesare, salvam:

```text
player_level_dataset.csv
team_match_dataset.csv
league_baseline.json
league_distributions.json
u_cluj_match_comparisons.json
u_cluj_tactical_weakness_report.json
tactical_clusters.json
anomaly_scores.csv
```

---

## 18. Endpoint-uri backend recomandate

### League baseline

```http
GET /api/league/baseline
```

Returneaza:

```text
league_baseline.json
```

---

### Analiza meci U Cluj

```http
GET /api/matches/{matchId}/tactical-weaknesses
```

Returneaza:

```text
u_cluj_tactical_weakness_report.json
```

---

### Tactical profile

```http
GET /api/matches/{matchId}/tactical-profile
```

Returneaza:

```json
{
  "matchId": 5715833,
  "teamName": "FC Universitatea Cluj",
  "clusterId": 1,
  "tacticalProfile": "high_loss_low_progression",
  "anomalyScore": 0.73
}
```

---

## 19. Notebook recomandat

Fisier:

```text
superliga_tactical_baseline_model.ipynb
```

Sectiuni:

```text
1. Load all players_stats.json files
2. Flatten player stats
3. Clean data
4. Aggregate to team-match level
5. Compute derived metrics
6. Compute league baselines
7. Compare U Cluj to baseline
8. Generate rule-based insights
9. Train IsolationForest
10. Train KMeans
11. Generate final report JSON
12. Export artifacts
```

---

## 20. Ordinea de lucru recomandata

```text
1. Pune toate fisierele `*_players_stats.json` intr-un folder
2. Scrie parser pentru players_stats.json
3. Creeaza player_level_dataset.csv
4. Fa mapping player/team daca este nevoie
5. Agrega la team-match level
6. Calculeaza metrici derivate
7. Calculeaza baseline si percentiles
8. Identifica meciurile U Cluj
9. Compara U Cluj cu baseline
10. Genereaza primele insights rule-based
11. Adauga IsolationForest
12. Adauga KMeans
13. Exporta raport JSON
14. Integreaza in backend
15. Afiseaza in frontend
```

---

## 21. Ce NU facem in acest model

Acest model NU face:

```text
pass vs shot vs carry la nivel de faza
decision score pe event
passing network real
heatmap reala pe teren
```

Pentru acelea avem nevoie de:

```text
match events
coordinates
timestamps
pass recipients
possession chains
```

Acest model face:

```text
comparatie cu liga
detectare slabiciuni tactice agregate
profil tactic
anomaly score
baseline Superliga
```

---

## 22. Cum se combina ulterior cu Decision Quality Model

Dupa ce acest model functioneaza, il combinam cu Decision Quality.

Combinare:

```text
Tactical Baseline Model:
  "U Cluj are probleme de progresie si pierderi"

Decision Quality Model:
  "A. Miron, I. Stoica si M. Thiam au multe decizii slabe"

Final Tactical Weakness Detector:
  "U Cluj progreseseaza greu deoarece anumiti jucatori aleg frecvent decizii cu valoare mica in build-up"
```

Aceasta va fi functionalitatea mare finala.

---

## 23. Pitch pentru hackathon

Varianta scurta:

```text
We trained a tactical baseline engine on all available real Superliga Wyscout matches from *_players_stats.json files. 
The system learns normal league performance levels and then compares U Cluj against that benchmark to detect tactical weaknesses like low progression, risky ball losses and poor final-third efficiency.
```

Varianta romana:

```text
Am construit un engine tactic antrenat pe toate meciurile reale din Superliga disponibile in fisierele *_players_stats.json. 
Sistemul invata care sunt valorile normale ale ligii si compara U Cluj cu acest baseline pentru a detecta automat slabiciuni tactice.
```
