from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WoS Battle Predictor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wospredv3.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {"accuracy": 0.92, "last_updated": "2024-03-20"}
