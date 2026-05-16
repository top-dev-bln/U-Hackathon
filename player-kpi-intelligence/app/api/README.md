# FastAPI - Player Data Endpoint

## Install dependencies

```bash
pip install -r requirements.txt
```

## Run API

```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

- `GET /health`
- `GET /players`

### Query params (`GET /players`)

- `cadence`: `weekly` (default) or `daily`
- `latest_only`: `true/false` (default `false`)
- `as_of_date`: optional `YYYY-MM-DD`

## Example

```bash
curl "http://127.0.0.1:8000/players?cadence=weekly&latest_only=true"
```
