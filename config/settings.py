import os

class Settings:
    PROJECT_NAME = "WOS Battle Predictor & AI Calibration System"
    VERSION = "1.0.0"
    API_V1_STR = "/api/v1"
    
    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:mgCfiNtyFueebETswIPkOUONmoaIHTns@postgres.railway.internal:5432/railway")
    
    # Simulation settings
    DEFAULT_ROUNDS = 20
    MAX_ROUNDS = 100

settings = Settings()
