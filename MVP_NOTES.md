# WOS Battle Predictor MVP Notes

## Local run

Backend:

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8080
```

Frontend:

```bash
cd frontend
python -m http.server 3000
```

Open `http://localhost:3000` and keep the backend API URL set to `http://localhost:8080`.

## Environment variables

Backend:

- `PORT`: Railway service port. Default is `8080`.
- `DATABASE_URL`: Optional Postgres connection string for future persistent storage.
- `CORS_ORIGINS`: Comma-separated allowed frontend origins.

Frontend:

- The static app stores the backend URL in browser localStorage through Settings.
- Local default is `http://localhost:8080`.
- Do not hardcode the Railway URL in source.

## MVP honesty rules

- Scout stats are treated as already including hero/base bonuses.
- Hero selections are recorded for calibration, but unverified hero skills are not applied.
- Troop-counter multipliers are not applied until verified source data is added.
- OCR upload accepts images and returns a manual-correction fallback until an OCR provider is configured.

## Deployment

Railway uses the root `Dockerfile` and `/health` for service checks.

Vercel serves the `frontend` directory. Set the backend URL in the app Settings after Railway deploys.

## Testing

Run:

```bash
python -m pytest
```

Current focused tests cover formation validation, prediction metadata, hero definitions, combat constants, health checks, and scout text parsing.
