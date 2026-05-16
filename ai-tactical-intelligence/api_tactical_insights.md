# Tactical Insights API (FastAPI)

## Pornire

```powershell
.\.venv\Scripts\python run_api.py
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Endpoint-uri

- `GET /api/health`
- `GET /api/league/baseline`
- `GET /api/league/distributions`
- `GET /api/matches/{match_id}/tactical-weaknesses`
- `GET /api/matches/{match_id}/tactical-profile`
- `POST /api/insights/from-players-stats`
- `POST /api/insights/compact/from-players-stats`
- `POST /api/insights/detailed/from-players-stats`
- `POST /api/insights/from-players-stats-multipart`
- `POST /api/insights/compact/from-players-stats-multipart`
- `POST /api/insights/detailed/from-players-stats-multipart`

## Input POST `from-players-stats`

```json
{
  "players_stats": {
    "players": []
  },
  "home_team_name": "Universitatea Cluj",
  "away_team_name": "UTA Arad",
  "match_id": 999001,
  "home_score": 1,
  "away_score": 0,
  "focus_team_name": "Universitatea Cluj"
}
```

Observatii:

- `players_stats` este JSON brut de tip Wyscout `players_stats`.
- Daca `match_id` lipseste, API-ul il infera sau genereaza unul sintetic.
- `focus_team_name` este optional; daca este setat, in raportul final ramane doar echipa respectiva.

## Output POST (rezumat)

Output-ul include:

- `finalReport` (raport final cu `overallWeaknessScore`, `riskLevel`, `tacticalProfile`, `anomalyScore`, `comparisons`, `insights`)
- `comparisons` (M6)
- `ruleBasedInsights` (M7 brut)
- `anomalyRowsForMatch` (M8)
- `tacticalClustersForMatch` (M9)

## Output POST `compact` (frontend)

Endpoint-urile `compact` returneaza o structura scurta:

- `match`
- `summary`
- `topInsights`
- `weaknessBreakdown`
- `strengths`

Exemplu:

```json
{
  "match": {
    "matchId": 900000000,
    "teamName": "Universitate Cluj",
    "opponent": "Botosani",
    "isHomeTeam": false
  },
  "summary": {
    "overallWeaknessScore": 0.4861,
    "riskLevel": "medium",
    "tacticalProfile": "high_loss_low_progression_with_chance_quality",
    "anomalyScore": 0.1282,
    "isAnomalous": false
  },
  "topInsights": [],
  "weaknessBreakdown": {
    "buildUp": 0.0,
    "ballLoss": 0.6481,
    "finalThird": 0.0,
    "pressing": 0.0,
    "duels": 0.2662
  },
  "strengths": []
}
```

Parametri query pentru `compact`:

- `top_insights` (default `2`, interval `1..10`)
- `top_strengths` (default `2`, interval `1..10`)

## Output POST `detailed` (ML/downstream)

Endpoint-urile `detailed` returneaza:

- `matchId`, `teamId`, `teamName`
- `baselineModel`
- `weaknessSignals`
- `metricComparisons` (toate metricile, cu `status` + `direction`)

## Input POST `from-players-stats-multipart`

Endpoint-ul primeste `multipart/form-data` cu:

- `players_stats_file` (fisier `.json`, obligatoriu)
- `home_team_name` (obligatoriu)
- `away_team_name` (obligatoriu)
- `match_id` (optional)
- `home_score` (optional)
- `away_score` (optional)
- `focus_team_name` (optional)

Exemplu `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/api/insights/from-players-stats-multipart" \
  -H "accept: application/json" \
  -F "players_stats_file=@Date - meciuri/Universitatea Cluj - UTA Arad, 1-0_players_stats.json;type=application/json" \
  -F "home_team_name=Universitatea Cluj" \
  -F "away_team_name=UTA Arad"
```

Exemplu `compact` multipart:

```bash
curl -X POST "http://127.0.0.1:8000/api/insights/compact/from-players-stats-multipart?top_insights=2&top_strengths=2" \
  -H "accept: application/json" \
  -F "players_stats_file=@Date - meciuri/Botosani - Universitate Cluj, 1-3_players_stats.json;type=application/json" \
  -F "home_team_name=Botosani" \
  -F "away_team_name=Universitate Cluj" \
  -F "focus_team_name=Universitate Cluj"
```

Exemplu `detailed` multipart:

```bash
curl -X POST "http://127.0.0.1:8000/api/insights/detailed/from-players-stats-multipart" \
  -H "accept: application/json" \
  -F "players_stats_file=@Date - meciuri/Botosani - Universitate Cluj, 1-3_players_stats.json;type=application/json" \
  -F "home_team_name=Botosani" \
  -F "away_team_name=Universitate Cluj" \
  -F "focus_team_name=Universitate Cluj"
```
