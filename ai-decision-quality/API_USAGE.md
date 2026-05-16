# Decision Quality API - Quick Start

## 1. Start API

```powershell
.\.venv\Scripts\uvicorn decision_quality_api:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI:

```text
http://localhost:8000/docs
```

## 2. Health Check

```powershell
curl http://localhost:8000/health
```

## 3. Analyze One Match (Full Insights)

Endpoint:

```text
POST /api/v1/matches/analyze
```

Body example:

```json
{
  "match_data": {
    "matches": []
  },
  "match_id": 99042601,
  "team_name": "FC Universitatea Cluj",
  "top_n": 10,
  "low_score_quantile": 0.25,
  "min_improvement": 0.02,
  "window_seconds": 10
}
```

Returns:
- summary pe meci
- jucatori care au performat bine
- jucatori care puteau performa mai bine
- faze bune / faze imbunatatibile
- faze care puteau fi transformate in shot/goal
- timeline si breakdown pe tip de decizie

## 4. Phase Decision (One Specific Event)

Endpoint:

```text
POST /api/v1/matches/phases/decision
```

Body example:

```json
{
  "match_data": {
    "matches": []
  },
  "match_id": 99042601,
  "team_name": "FC Universitatea Cluj",
  "event_id": 880100003
}
```

Returns:
- decizia reala
- alternativele (pass/shot/carry)
- cea mai buna decizie estimata
- potential gain

## 5. Players-Only Insights

Endpoint:

```text
POST /api/v1/matches/players/insights
```

Body: acelasi ca la `/api/v1/matches/analyze`.

## 6. Upload .json (multipart/form-data)

Endpoint principal (upload fisier):

```text
POST /api/v1/matches/analyze/upload
```

Exemplu:

```powershell
curl -X POST "http://localhost:8000/api/v1/matches/analyze/upload" `
  -F "file=@u_cluj_10_matches_wyscout_events_combined.json;type=application/json" `
  -F "match_id=99042601" `
  -F "team_name=FC Universitatea Cluj" `
  -F "top_n=10"
```

Endpointuri upload suplimentare:

```text
POST /api/v1/matches/players/insights/upload
POST /api/v1/matches/phases/decision/upload
```

Exemplu phase decision upload:

```powershell
curl -X POST "http://localhost:8000/api/v1/matches/phases/decision/upload" `
  -F "file=@u_cluj_10_matches_wyscout_events_combined.json;type=application/json" `
  -F "match_id=99042601" `
  -F "team_name=FC Universitatea Cluj" `
  -F "event_id=880100003"
```

## 7. Test Rapid Din Swagger (/docs)

Pentru test fara upload sau JSON mare in body:

```text
POST /api/v1/demo/matches/analyze
POST /api/v1/demo/matches/players/insights
POST /api/v1/demo/matches/phases/decision
```

In `/docs`, poti da `Try it out` si `Execute` direct cu body `{}`.
API foloseste automat fisierul local `u_cluj_10_matches_wyscout_events_combined.json`.
