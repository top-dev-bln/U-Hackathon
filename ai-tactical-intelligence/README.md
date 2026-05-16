# Tactical Insights API (Superliga / Wyscout)

Pipeline Python care proceseaza fisiere `*_players_stats.json`, construieste baseline tactic si expune insights prin FastAPI.

## Cerinte

- Python 3.11+ (testat local pe 3.13)
- pip

## Instalare

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Structura

- `src/tactical_baseline/` - logica pipeline + servicii API
- `run_pipeline.py` - ruleaza pipeline-ul M0-M11
- `run_api.py` - porneste FastAPI
- `Date - meciuri/` - input raw (`*_players_stats.json`) (neversionat)
- `outputs/` - artefacte generate (neversionat)

## Rulare pipeline

```powershell
.\.venv\Scripts\python run_pipeline.py
```

## Rulare API

```powershell
.\.venv\Scripts\python run_api.py
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Endpointuri principale

- `POST /api/insights/from-players-stats`
- `POST /api/insights/from-players-stats-multipart`
- `POST /api/insights/compact/from-players-stats`
- `POST /api/insights/compact/from-players-stats-multipart`
- `POST /api/insights/detailed/from-players-stats`
- `POST /api/insights/detailed/from-players-stats-multipart`

## Formate output

- `compact`: optimizat pentru frontend (`match`, `summary`, `topInsights`, `weaknessBreakdown`, `strengths`)
- `detailed`: optimizat pentru ML/downstream (`baselineModel`, `weaknessSignals`, `metricComparisons`)

Pentru exemple complete de request/response:
- `api_tactical_insights.md`

