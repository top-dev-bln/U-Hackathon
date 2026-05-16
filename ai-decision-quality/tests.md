# API Tests - Decision Quality

## 1. Start API

```powershell
.\.venv\Scripts\uvicorn decision_quality_api:app --host 0.0.0.0 --port 8000 --reload
```

Base URL:

```text
http://localhost:8000
```

## 2. Test Setup (PowerShell)

```powershell
$base = "http://localhost:8000"
$jsonPath = ".\u_cluj_10_matches_wyscout_events_combined.json"
$matchData = Get-Content $jsonPath -Raw | ConvertFrom-Json
```

## 3. GET /health

```powershell
Invoke-RestMethod -Method Get -Uri "$base/health"
```

## 4. GET /api/v1/model/info

```powershell
Invoke-RestMethod -Method Get -Uri "$base/api/v1/model/info"
```

Optional model path:

```powershell
Invoke-RestMethod -Method Get -Uri "$base/api/v1/model/info?model_path=u_cluj_decision_quality_model.joblib"
```

## 5. POST /api/v1/matches/analyze (JSON body)

```powershell
$body = @{
  match_data = $matchData
  match_id = 99042601
  team_name = "FC Universitatea Cluj"
  low_score_quantile = 0.25
  min_improvement = 0.02
  min_player_actions = 8
  top_n = 10
  window_seconds = 10
  model_path = "u_cluj_decision_quality_model.joblib"
} | ConvertTo-Json -Depth 100

Invoke-RestMethod -Method Post `
  -Uri "$base/api/v1/matches/analyze" `
  -ContentType "application/json" `
  -Body $body
```

## 6. POST /api/v1/matches/analyze/upload (multipart .json)

```powershell
curl.exe -X POST "$base/api/v1/matches/analyze/upload" `
  -F "file=@$jsonPath;type=application/json" `
  -F "match_id=99042601" `
  -F "team_name=FC Universitatea Cluj" `
  -F "top_n=10" `
  -F "low_score_quantile=0.25" `
  -F "min_improvement=0.02" `
  -F "window_seconds=10"
```

## 7. POST /api/v1/matches/players/insights (JSON body)

```powershell
$body = @{
  match_data = $matchData
  match_id = 99042601
  team_name = "FC Universitatea Cluj"
  top_n = 10
} | ConvertTo-Json -Depth 100

Invoke-RestMethod -Method Post `
  -Uri "$base/api/v1/matches/players/insights" `
  -ContentType "application/json" `
  -Body $body
```

## 8. POST /api/v1/matches/players/insights/upload (multipart .json)

```powershell
curl.exe -X POST "$base/api/v1/matches/players/insights/upload" `
  -F "file=@$jsonPath;type=application/json" `
  -F "match_id=99042601" `
  -F "team_name=FC Universitatea Cluj" `
  -F "top_n=10"
```

## 9. POST /api/v1/matches/phases/decision (JSON body)

By `event_id`:

```powershell
$body = @{
  match_data = $matchData
  match_id = 99042601
  team_name = "FC Universitatea Cluj"
  event_id = 880100003
} | ConvertTo-Json -Depth 100

Invoke-RestMethod -Method Post `
  -Uri "$base/api/v1/matches/phases/decision" `
  -ContentType "application/json" `
  -Body $body
```

By `minute/second/player_name`:

```powershell
$body = @{
  match_data = $matchData
  match_id = 99042601
  team_name = "FC Universitatea Cluj"
  minute = 0
  second = 11
  player_name = "O. Bic"
} | ConvertTo-Json -Depth 100

Invoke-RestMethod -Method Post `
  -Uri "$base/api/v1/matches/phases/decision" `
  -ContentType "application/json" `
  -Body $body
```

## 10. POST /api/v1/matches/phases/decision/upload (multipart .json)

```powershell
curl.exe -X POST "$base/api/v1/matches/phases/decision/upload" `
  -F "file=@$jsonPath;type=application/json" `
  -F "match_id=99042601" `
  -F "team_name=FC Universitatea Cluj" `
  -F "event_id=880100003"
```

## 11. Quick Negative Tests

Invalid file extension:

```powershell
curl.exe -X POST "$base/api/v1/matches/analyze/upload" -F "file=@.\notebook.ipynb"
```

Expected: `400` with message that only `.json` is supported.

Missing selector for phase endpoint:

```powershell
$body = @{
  match_data = $matchData
  match_id = 99042601
} | ConvertTo-Json -Depth 100

Invoke-RestMethod -Method Post `
  -Uri "$base/api/v1/matches/phases/decision" `
  -ContentType "application/json" `
  -Body $body
```

Expected: `422` because `event_id` or `minute/second` is required.

## 12. Notes

- Daca JSON-ul contine mai multe meciuri, trimite `match_id`.
- Pentru fisiere mari, foloseste endpointurile `/upload`.
- Pentru debugging rapid, foloseste Swagger la `http://localhost:8000/docs`.

## 13. Test Rapid Direct Din `/docs` (fara upload)

Foloseste endpointurile demo:

```text
POST /api/v1/demo/matches/analyze
POST /api/v1/demo/matches/players/insights
POST /api/v1/demo/matches/phases/decision
```

In Swagger:

1. Deschide `http://localhost:8000/docs`.
2. Selecteaza unul din endpointurile `demo`.
3. Apasa `Try it out`.
4. Pentru test rapid, lasa body-ul `{}` si apasa `Execute`.

Aceste endpointuri folosesc implicit fisierul local:

```text
u_cluj_10_matches_wyscout_events_combined.json
```

Optional, poti schimba in body:
- `sample_json_path`
- `match_id`
- `team_name`
- `event_id` (pentru phase decision)
