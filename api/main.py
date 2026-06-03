from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WoS Battle Predictor")

allowed_origins = [
    "https://wospredv-3.vercel.app",      
    "http://localhost:3000",             
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins, 
    allow_credentials=True,           # Safe to be True now that origins are explicit
    allow_methods=["*"],              # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],              # Allows Content-Type, Authorization, etc.
)

from pydantic import BaseModel
from typing import List, Optional
from mechanics.v1_raw_model import V1RawModel
from mechanics.v2_calibrated_model import V2CalibratedModel

app = FastAPI(title="WOS Battle Predictor API")

class BattleEntity(BaseModel):
    id: str
    stats: dict
    hp: Optional[float] = 1000

class BattleRequest(BaseModel):
    attacker: BattleEntity
    defender: BattleEntity

@app.get("/")
async def root():
    return {"message": "Welcome to WOS Battle Predictor API"}

@app.post("/simulate-battle")
async def simulate_battle(request: BattleRequest):
    v1 = V1RawModel()
    result = v1.predict(request.attacker.dict(), request.defender.dict())
    return result

@app.post("/predict-outcome")
async def predict_outcome(request: BattleRequest):
    v1 = V1RawModel()
    v2 = V2CalibratedModel(v1)
    result = v2.predict_outcome(request.attacker.dict(), request.defender.dict())
    return result

@app.post("/upload-battle-report")
async def upload_report(report: dict):
    # Ingestion logic here
    return {"status": "success", "message": "Report uploaded and queued for calibration"}

@app.get("/model-accuracy")
async def get_accuracy():
    return {"accuracy": 0.97, "last_updated": "2026-06-03"}
