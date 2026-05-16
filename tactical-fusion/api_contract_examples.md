# Tactical Fusion API Contract Examples

## Endpoint
- Method: `POST`
- Path: `/fusion/analysis/json`
- Content-Type: `application/json`

## Request body
```json
{
  "input1": { "...": "Tactical Baseline payload" },
  "input2": { "...": "Decision Quality payload" }
}
```

## Multipart request (files)
- Content-Type: `multipart/form-data`
- Path: `/fusion/analysis/multipart`
- Required form fields:
  - `input1` (JSON file)
  - `input2` (JSON file)
- Both files must be `.json` and contain JSON objects.

Example curl:
```bash
curl -X POST "http://127.0.0.1:8080/fusion/analysis/multipart" \
  -F "input1=@input1.json;type=application/json" \
  -F "input2=@input2.json;type=application/json"
```

JSON curl:
```bash
curl -X POST "http://127.0.0.1:8080/fusion/analysis/json" \
  -H "Content-Type: application/json" \
  -d "{\"input1\": {...}, \"input2\": {...}}"
```

Legacy compatibility:
- `POST /fusion/analysis` remains available (accepts both JSON body and multipart), but it is hidden from Swagger.

## Example response shape
```json
{
  "fusionOutput": {
    "combinedInsights": [],
    "playerPriorities": [],
    "trainingFocus": []
  },
  "frontendOutput": {
    "headline": "...",
    "topProblems": [],
    "recommendations": []
  },
  "meta": {
    "baselineSignals": 0,
    "decisionSignals": 0,
    "fusedCategories": 0
  }
}
```

## Health check
- Method: `GET`
- Path: `/health`
- Response:
```json
{
  "status": "ok"
}
```
