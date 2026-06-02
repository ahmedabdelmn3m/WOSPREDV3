# WOS Battle Predictor & AI Calibration System

A production-ready system for simulating Whiteout Survival (WOS) battles, predicting outcomes, and calibrating accuracy using AI.

## Architecture

- **Core Engine (V1)**: Deterministic combat simulation using official formulas.
- **Skill Engine**: Event-driven system for hero skills (damage multipliers, shields, heals).
- **AI Calibration (V2)**: Learning layer that optimizes prediction weights based on real battle reports.
- **API**: FastAPI-based REST interface for simulation and prediction.

## Directory Structure

- `core-engine/`: Mathematical combat formulas and turn resolution.
- `mechanics/`: V1 (Deterministic) and V2 (AI-Calibrated) models.
- `skills/`: Event-driven skill engine.
- `ai_calibration/`: Learning and optimization logic.
- `api/`: FastAPI routes and schemas.
- `database/`: PostgreSQL schema definitions.

## Getting Started

### Prerequisites
- Python 3.9+
- Docker & Docker Compose

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run with Docker: `docker-compose up`

### API Usage
- `POST /simulate-battle`: Run a V1 deterministic simulation.
- `POST /predict-outcome`: Get a V2 calibrated win probability.
- `POST /upload-battle-report`: Submit real data for AI learning.

## Testing
Run tests using:
```bash
python -m unittest discover tests
```
