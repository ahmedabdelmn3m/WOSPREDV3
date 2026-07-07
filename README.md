# WOSPREDV3 — Battle Intelligence Platform

## Strategy Update v1

This repo now includes the War Decision Machine strategy package:

- `frontend/strategy-guide.html` exposes the scout-evidence strategy live in the active frontend.
- `docs/war-decision-machine/` stores the feature plan, scout concept, integration notes, and reference TypeScript starter engine.
- `schemas/battle-input.schema.json` and `schemas/ocr-capture.schema.json` define future battle-input and OCR capture shapes.
- `examples/` includes sample battle input and prediction output.

This update does not change battle formulas, hero mechanics, troop tier logic, or existing API payloads. It makes the strategy guide visible and reviewable before any future engine conversion.

Live test paths after Vercel deploy:

- `/strategy-guide.html`
- `/qa.html`
- `/`

Combat simulation and prediction engine for **Whiteout Survival**.

---

## Architecture

```
GitHub repo  ──►  Railway (FastAPI backend)
                        ▲
             Vercel (static frontend)
                        │
                   User browser
```

| Layer    | Tech              | Host    |
|----------|-------------------|---------|
| Frontend | HTML / CSS / JS   | Vercel  |
| Backend  | Python / FastAPI  | Railway |
| Database | PostgreSQL 15     | Railway |

---

## Verified Combat Formulas

```
damage  = (attack × (1 + Σ attack_bonus)  × lethality × (1 + Σ lethality_bonus)) / 100
defense = (defense × (1 + Σ defense_bonus) × health   × (1 + Σ health_bonus))    / 100
```

---

## Project Structure

```
wospredv3/
├── core_engine/
│   ├── damage_model.py        # Verified damage formula
│   ├── defense_model.py       # Verified defense formula
│   ├── troop_stats.py         # TroopTypeStats, Formation, ArmyStats
│   ├── turn_resolver.py       # Single-round combat resolution
│   ├── battle_simulator.py    # Full round-based simulation
│   ├── combat_engine.py       # Engine entry point
│   ├── prediction_engine.py   # Win prob + strength analysis
│   ├── reverse_optimizer.py   # What stats do I need to win?
│   ├── formation_optimizer.py # Best formation for a matchup
│   └── preset_manager.py      # Save/load army configs
├── mechanics/
│   ├── v1_raw_model.py        # Deterministic model
│   └── v2_calibrated_model.py # Probability model
├── api/
│   └── main.py                # FastAPI app + all routes
├── database/
│   └── schema.sql             # Full PostgreSQL schema
├── frontend/
│   ├── index.html             # Single-page app
│   ├── styles.css             # WOS arctic theme
│   ├── app.js                 # All UI logic
│   └── config.js              # API URL config
├── tests/
│   └── test_damage.py         # 26 passing tests
├── Dockerfile
├── railway.toml
├── vercel.json
├── docker-compose.yml
└── requirements.txt
```

---

## 1 — Prerequisites

Install these before starting:

| Tool       | Version | Download |
|------------|---------|----------|
| Python     | 3.11+   | python.org |
| Git        | any     | git-scm.com |
| Docker     | optional | docker.com |

---

## 2 — GitHub Setup

### 2a. Push your code

```bash
cd your-project-folder

# If not already a git repo
git init
git branch -M main

# Add remote (replace with your repo URL)
git remote add origin https://github.com/ahmedabdelmn3m/WOSPREDV3.git

# Stage and push all files
git add .
git commit -m "feat: complete v2 deployment-ready build"
git push -u origin main
```

### 2b. Clean up the duplicate folder

Before pushing, **delete the `core-engine/` folder** (hyphen version).
Only `core_engine/` (underscore) should exist — Python cannot import hyphenated names.

```bash
git rm -r core-engine/
git commit -m "fix: remove duplicate core-engine hyphen folder"
git push
```

---

## 3 — Railway (Backend)

### 3a. Create project

1. Go to **railway.app** → **New Project**
2. Choose **Deploy from GitHub repo**
3. Select `ahmedabdelmn3m/WOSPREDV3`
4. Railway will auto-detect the `Dockerfile`

### 3b. Add PostgreSQL (optional for V1)

V1 works without a database (in-memory presets).
To enable full persistence:

1. In your Railway project → **+ New** → **Database** → **PostgreSQL**
2. Railway creates the DB and sets `DATABASE_URL` automatically
3. Run the schema:
   - Go to Railway PostgreSQL → **Connect** tab → copy the connection string
   - Run: `psql YOUR_CONNECTION_STRING -f database/schema.sql`

### 3c. Environment variables

In Railway → your service → **Variables** tab, set:

| Variable | Value |
|----------|-------|
| `PORT`   | `8080` |

`DATABASE_URL` is set automatically if you added a Railway PostgreSQL service.

### 3d. Verify deployment

1. Railway → your service → **Deployments** → watch logs
2. Once green, click the generated domain (e.g., `wospredv3-production.up.railway.app`)
3. You should see the API info JSON:
```json
{ "service": "WOS Battle Intelligence API", "version": "2.0.0", ... }
```

**Copy this URL — you need it for Vercel.**

---

## 4 — Vercel (Frontend)

### 4a. Create project

1. Go to **vercel.com** → **Add New Project**
2. Import from GitHub → select `WOSPREDV3`
3. Configure:
   - **Framework Preset**: Other
   - **Root Directory**: `frontend`
   - **Build Command**: *(leave empty)*
   - **Output Directory**: `.`
4. Click **Deploy**

Production frontend note:
- `frontend/` is the active Vercel frontend.
- Root-level `index.html`, `app.js`, and `config.js` are older duplicated files and should not be treated as production unless Vercel is deliberately reconfigured.
- The active browser API config is `frontend/config.js`.
- Live QA is available at `/qa.html` after deployment. Use it after every Codex change.

### 4b. Connect frontend to backend

The default API URL in `frontend/config.js` is:

```text
https://wospredv3-production.up.railway.app
```

To change it from the browser:
1. Open the Vercel app.
2. Click **API Settings**.
3. Paste the Railway URL.
4. Click **Save & Reconnect**.

This URL is stored in browser `localStorage` under `wos_api_url`.

### 4c. Live QA after changes

After every Codex change and Vercel deploy:
1. Open the Vercel app.
2. Open **Live QA** in the header or visit `/qa.html`.
3. Confirm every core API check shows `PASS`.
4. Return to the Battle Predictor and run the normal prediction and formation actions.

More detail: `docs/live-qa.md`.

---

## 5 — Local Development

### 5a. Python only (no Docker)

```bash
# Clone repo
git clone https://github.com/ahmedabdelmn3m/WOSPREDV3.git
cd WOSPREDV3

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn api.main:app --reload --port 8080
```

Open `frontend/index.html` in a browser, or serve it with:
```bash
cd frontend && python -m http.server 3000
```

The default frontend API URL is the live Railway URL. To test a local backend, open **API Settings** in the browser and save `http://localhost:8080`.

### 5b. Docker Compose (with database)

```bash
docker compose up --build
```

- API: http://localhost:8080
- Database auto-initialized with schema.sql
- Frontend: open `frontend/index.html` directly

---

## 6 — API Reference

| Method | Endpoint              | Description |
|--------|-----------------------|-------------|
| GET    | `/`                   | Health check + formula reference |
| POST   | `/simulate-battle`    | V1 deterministic round simulation |
| POST   | `/predict-outcome`    | V2 win probability + strength analysis |
| POST   | `/army-preview`       | Inspect effective stats for one army |
| POST   | `/reverse-optimize`   | Find min stat upgrades to reach win target |
| POST   | `/formation/optimize` | Rank all 14 standard formations |
| GET    | `/presets`            | List saved presets |
| POST   | `/presets`            | Save a preset |
| GET    | `/presets/{name}`     | Load a preset |
| DELETE | `/presets/{name}`     | Delete a preset |
| POST   | `/feedback`           | Submit post-battle outcome |
| GET    | `/model-accuracy`     | Current model stats |

### Example: predict-outcome

```bash
curl -X POST https://YOUR-RAILWAY-URL/predict-outcome \
  -H "Content-Type: application/json" \
  -d '{
    "attacker": {
      "name": "Ahmed",
      "infantry":  { "attack_pct": 150, "defense_pct": 120, "health_pct": 200, "lethality_pct": 80 },
      "lancer":    { "attack_pct": 100, "defense_pct": 100, "health_pct": 150, "lethality_pct": 60 },
      "marksman":  { "attack_pct": 200, "defense_pct": 110, "health_pct": 160, "lethality_pct": 90 },
      "formation": { "infantry": 0.50, "lancer": 0.20, "marksman": 0.30 },
      "troop_count": 500000
    },
    "defender": {
      "name": "Enemy",
      "infantry":  { "attack_pct": 130, "defense_pct": 110, "health_pct": 180, "lethality_pct": 70 },
      "lancer":    { "attack_pct": 90,  "defense_pct": 90,  "health_pct": 130, "lethality_pct": 55 },
      "marksman":  { "attack_pct": 180, "defense_pct": 100, "health_pct": 150, "lethality_pct": 80 },
      "formation": { "infantry": 0.50, "lancer": 0.20, "marksman": 0.30 },
      "troop_count": 400000
    }
  }'
```

---

## 7 — Running Tests

```bash
cd WOSPREDV3
python -m pytest tests/ -v
```

Expected: **26 tests, all passing**.

Tests cover:
- Damage formula correctness (and confirm it's not inverted)
- Defense formula correctness
- TroopTypeStats from_percentages()
- Formation validation
- ArmyStats weighted stats
- Full battle simulation integration

---

## 8 — Environment Variables Reference

| Variable       | Required | Default | Description |
|----------------|----------|---------|-------------|
| `PORT`         | Yes (Railway) | `8080` | Port the API listens on |
| `DATABASE_URL` | No (V1)  | None    | PostgreSQL connection string for persistent presets |

---

## 9 — Troubleshooting

### Railway deployment fails
- Check **Deployments** tab logs in Railway
- Confirm `Dockerfile` is at the project root
- Confirm `PORT` variable is set to `8080` in Railway Variables

### `ModuleNotFoundError: core_engine`
- You still have the `core-engine/` (hyphen) folder. Delete it:
  ```bash
  git rm -r core-engine/
  git commit -m "fix: remove hyphenated folder"
  git push
  ```

### Frontend shows "⬤ Offline"
- Click ⚙ Settings and confirm the Railway URL is correct
- Check that Railway is running (no red deployments)
- Make sure CORS is enabled (it is, by default in this API)

### Formation validation error (must sum to 100%)
- Infantry + Lancer + Marksman must equal exactly 100
- The form shows a red `Total: X%` indicator when invalid

### API returns `422 Unprocessable Entity`
- Most common cause: formation fractions don't sum to 1.0
- Example: `{"infantry": 0.50, "lancer": 0.20, "marksman": 0.30}` = correct ✓
- Example: `{"infantry": 50, "lancer": 20, "marksman": 30}` = wrong ✗ (use decimals)

---

## 10 — What's Next (Tier 3+)

Remaining systems to build:
- **OCR**: Screenshot upload → auto-extract stats
- **Hero System**: Hero skill effects on combat
- **Learning Engine**: Improve predictions from real battle reports
- **Database presets**: Persist presets across devices with user accounts
