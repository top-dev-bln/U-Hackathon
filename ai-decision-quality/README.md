# Decision Quality Model (Football)

API + pipeline pentru evaluarea calitatii deciziilor ofensive (`pass`, `shot`, `carry`) pe baza evenimentelor de meci (Wyscout-style).

## Ce face proiectul

- antreneaza model ML pe evenimente flat (`decision_quality_pipeline.py`)
- calculeaza `decisionValue` pe fiecare faza
- propune `suggestedAlternative` cand faza este slaba
- agrega scoruri pe jucatori
- expune analiza prin FastAPI (`decision_quality_api.py`)

## Structura

- `decision_quality_pipeline.py` - training + export predicții
- `decision_quality_api.py` - endpointuri API
- `decision_phase_recommender.py` - utilitar CLI pentru o faza specifica
- `u_cluj_10_matches_flat_ml_dataset.csv` - dataset flat pentru training
- `u_cluj_10_matches_wyscout_events_combined.json` - sample JSON meciuri
- `u_cluj_decision_quality_model.joblib` - model antrenat (ready-to-use)
- `u_cluj_decision_quality_model_report.json` - raport model
- `API_USAGE.md` - usage rapid
- `tests.md` - checklist complet de testare endpointuri

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Re-train model

```powershell
.\.venv\Scripts\python decision_quality_pipeline.py --model auto
```

## Run API

```powershell
.\.venv\Scripts\uvicorn decision_quality_api:app --host 0.0.0.0 --port 8000 --reload
```

Swagger:

```text
http://localhost:8000/docs
```

## Endpointuri principale

- `POST /api/v1/matches/analyze`
- `POST /api/v1/matches/analyze/upload`
- `POST /api/v1/matches/players/insights`
- `POST /api/v1/matches/phases/decision`
- `POST /api/v1/demo/matches/analyze` (test rapid din docs)

## Notă

Endpointurile `/upload` primesc `.json` brut de meci. Nu trebuie preprocesat.
