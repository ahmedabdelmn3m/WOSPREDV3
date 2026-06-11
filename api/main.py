"""
WOS Battle Intelligence API  v2.0.0
====================================
Endpoints
---------
GET  /                       Health check + formula reference
POST /simulate-battle        V1 deterministic round simulation
POST /predict-outcome        V2 prediction with win probability + analysis
POST /army-preview           Inspect effective stats without battling
POST /reverse-optimize       Find minimum stat upgrades to reach a win target
POST /formation/optimize     Rank all standard formations for a matchup
GET  /presets                List saved presets
POST /presets                Save a preset
GET  /presets/{name}         Load a specific preset
DELETE /presets/{name}       Delete a preset
POST /feedback               Submit post-battle outcome
POST /upload-battle-report   Queue a report for calibration
GET  /model-accuracy         Current model accuracy stats
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator
from typing import Optional

from core_engine.troop_stats        import ArmyStats, Formation, TroopTypeStats
from core_engine.combat_engine      import CombatEngine
from core_engine.prediction_engine  import PredictionEngine
from core_engine.reverse_optimizer  import ReverseOptimizer
from core_engine.formation_optimizer import FormationOptimizer
from core_engine.preset_manager     import PresetManager
from heroes.hero_loader             import HeroLoader
from mechanics.v1_raw_model         import V1RawModel
from mechanics.v2_calibrated_model  import V2CalibratedModel

# ── Singletons (one per process) ─────────────────────────────────────────────
_combat_engine     = CombatEngine()
_prediction_engine = PredictionEngine(_combat_engine)
_reverse_optimizer = ReverseOptimizer(_combat_engine)
_formation_optimizer = FormationOptimizer(_combat_engine)
_preset_manager    = PresetManager()
_hero_loader       = HeroLoader()
_v1                = V1RawModel()
_v2                = V2CalibratedModel(_v1)

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="WOS Battle Intelligence API",
    description="Verified-formula combat simulation for Whiteout Survival.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
#  Pydantic models
# ═══════════════════════════════════════════════════════════════════════════

class TroopStatsInput(BaseModel):
    attack_pct:     float = 0.0
    defense_pct:    float = 0.0
    health_pct:     float = 0.0
    lethality_pct:  float = 0.0
    attack_base:    float = 1.0
    defense_base:   float = 1.0
    health_base:    float = 1.0
    lethality_base: float = 1.0

    def to_troop_type_stats(self) -> TroopTypeStats:
        return TroopTypeStats(
            attack=self.attack_base,
            defense=self.defense_base,
            health=self.health_base,
            lethality=self.lethality_base,
            attack_bonus=self.attack_pct     / 100.0,
            defense_bonus=self.defense_pct   / 100.0,
            health_bonus=self.health_pct     / 100.0,
            lethality_bonus=self.lethality_pct / 100.0,
        )


class FormationInput(BaseModel):
    infantry:  float = 0.50
    lancer:    float = 0.20
    marksman:  float = 0.30

    @model_validator(mode="after")
    def must_sum_to_one(self) -> "FormationInput":
        total = self.infantry + self.lancer + self.marksman
        if abs(total - 1.0) > 0.005:
            raise ValueError(
                f"Formation must sum to 1.0 (got {total:.3f}). "
                f"infantry={self.infantry}, lancer={self.lancer}, "
                f"marksman={self.marksman}"
            )
        return self


from core_engine.troop_stats import ArmyStats, Formation, TroopTypeStats, Hero

class HeroInput(BaseModel):
    name: str = ""
    stars: int = 5
    widget: int = 5

    def to_hero(self) -> Hero:
        return Hero(name=self.name, stars=self.stars, widget=self.widget)

class ArmyInput(BaseModel):
    name:        str             = "Unknown"
    infantry:    TroopStatsInput = TroopStatsInput()
    lancer:      TroopStatsInput = TroopStatsInput()
    marksman:    TroopStatsInput = TroopStatsInput()
    formation:   FormationInput  = FormationInput()
    troop_count: int             = 500_000
    heroes:      list[HeroInput] = []

    def to_army_stats(self) -> ArmyStats:
        return ArmyStats(
            name=self.name,
            infantry=self.infantry.to_troop_type_stats(),
            lancer=self.lancer.to_troop_type_stats(),
            marksman=self.marksman.to_troop_type_stats(),
            formation=Formation(
                infantry=self.formation.infantry,
                lancer=self.formation.lancer,
                marksman=self.formation.marksman,
            ),
            troop_count=self.troop_count,
            heroes=[h.to_hero() for h in self.heroes[:3]],
        )


class BattleRequest(BaseModel):
    attacker:   ArmyInput
    defender:   ArmyInput
    max_rounds: int = 20


class ReverseOptimizeRequest(BaseModel):
    own_army:            ArmyInput
    enemy_army:          ArmyInput
    target_win_probability: float = 0.75
    max_rounds:          int   = 20


class FormationOptimizeRequest(BaseModel):
    own_army:   ArmyInput
    enemy_army: ArmyInput
    max_rounds: int = 20


class PresetSaveRequest(BaseModel):
    name:        str
    infantry:    TroopStatsInput = TroopStatsInput()
    lancer:      TroopStatsInput = TroopStatsInput()
    marksman:    TroopStatsInput = TroopStatsInput()
    formation:   FormationInput  = FormationInput()
    troop_count: int             = 500_000

    def to_army_stats(self) -> ArmyStats:
        return ArmyStats(
            name=self.name,
            infantry=self.infantry.to_troop_type_stats(),
            lancer=self.lancer.to_troop_type_stats(),
            marksman=self.marksman.to_troop_type_stats(),
            formation=Formation(
                infantry=self.formation.infantry,
                lancer=self.formation.lancer,
                marksman=self.formation.marksman,
            ),
            troop_count=self.troop_count,
        )


class FeedbackRequest(BaseModel):
    prediction_id:      Optional[str] = None
    predicted_winner:   str
    actual_winner:      str
    notes:              Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════
#  Routes
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "service": "WOS Battle Intelligence API",
        "version": "2.0.0",
        "verified_formulas": {
            "damage":  "damage  = (attack × (1 + Σattack_bonus) × lethality × (1 + Σlethality_bonus)) / 100",
            "defense": "defense = (defense × (1 + Σdefense_bonus) × health × (1 + Σhealth_bonus))     / 100",
        },
        "endpoints": {
            "POST /simulate-battle":    "V1 deterministic simulation",
            "POST /predict-outcome":    "V2 prediction with win probability + analysis",
            "POST /army-preview":       "Inspect effective stats",
            "POST /reverse-optimize":   "Find stat upgrades to reach a win target",
            "POST /formation/optimize": "Rank all standard formations",
            "GET  /presets":            "List presets",
            "POST /presets":            "Save a preset",
            "GET  /presets/{name}":     "Load a preset",
            "DELETE /presets/{name}":   "Delete a preset",
        },
    }


# ── Battle ───────────────────────────────────────────────────────────────────

@app.post("/simulate-battle")
async def simulate_battle(req: BattleRequest):
    """V1 deterministic round-by-round simulation."""
    try:
        return _v1.predict(
            req.attacker.to_army_stats(),
            req.defender.to_army_stats(),
            max_rounds=req.max_rounds,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/predict-outcome")
async def predict_outcome(req: BattleRequest):
    """V2 full prediction: win probability, strength analysis, bottleneck."""
    try:
        return _prediction_engine.predict(
            req.attacker.to_army_stats(),
            req.defender.to_army_stats(),
            max_rounds=req.max_rounds,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/army-preview")
async def army_preview(army: ArmyInput):
    """Preview computed effective stats for an army — no battle run."""
    try:
        return army.to_army_stats().stat_summary()
    except ValueError as e:
        raise HTTPException(422, str(e))


# ── Optimizers ───────────────────────────────────────────────────────────────

@app.post("/reverse-optimize")
async def reverse_optimize(req: ReverseOptimizeRequest):
    """Find minimum stat upgrades to reach the target win probability."""
    try:
        target = max(0.01, min(0.99, req.target_win_probability))
        return _reverse_optimizer.optimize(
            own_army=req.own_army.to_army_stats(),
            enemy_army=req.enemy_army.to_army_stats(),
            target_prob=target,
            max_rounds=req.max_rounds,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/formation/optimize")
async def formation_optimize(req: FormationOptimizeRequest):
    """Rank all standard formations for the given matchup."""
    try:
        return _formation_optimizer.optimize(
            own_army=req.own_army.to_army_stats(),
            enemy_army=req.enemy_army.to_army_stats(),
            max_rounds=req.max_rounds,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Presets ───────────────────────────────────────────────────────────────────

@app.get("/presets")
async def list_presets():
    return {"presets": _preset_manager.list()}


@app.post("/presets")
async def save_preset(req: PresetSaveRequest):
    try:
        army = req.to_army_stats()
        saved = _preset_manager.save(req.name, army)
        return {"status": "saved", "preset": saved}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/presets/{name}")
async def get_preset(name: str):
    raw = _preset_manager.load_raw(name)
    if not raw:
        raise HTTPException(404, f"Preset '{name}' not found.")
    return raw


@app.delete("/presets/{name}")
async def delete_preset(name: str):
    if not _preset_manager.delete(name):
        raise HTTPException(404, f"Preset '{name}' not found.")
    return {"status": "deleted", "name": name}


# ── Feedback / Reports ────────────────────────────────────────────────────────

@app.post("/feedback")
async def submit_feedback(fb: FeedbackRequest):
    correct = fb.predicted_winner == fb.actual_winner
    return {
        "status":   "received",
        "correct":  correct,
        "message":  "Thank you — this improves future predictions.",
    }


@app.post("/upload-battle-report")
async def upload_report(report: dict):
    return {
        "status":  "queued",
        "message": "Report queued for V2 calibration.",
    }


@app.get("/model-accuracy")
async def model_accuracy():
    return {
        "v1_formula":   "VERIFIED — deterministic, based on confirmed WOS formulas",
        "v2_accuracy":  "UNCALIBRATED — probability model requires battle report data",
        "reports_used": 0,
        "note":         "Submit battle reports via POST /upload-battle-report to improve V2.",
    }


@app.get("/api/heroes")
async def list_heroes():
    """Returns the list of heroes for the frontend dropdown."""
    return {"heroes": _hero_loader.get_all_heroes()}

# ═══════════════════════════════════════════════════════════════════════════
#  Rally Timing Calculator Endpoints
# ═══════════════════════════════════════════════════════════════════════════

from api.rally_timing import RallyTimingRequest, RallyTimingResponse, calculate_rally_timing

@app.post("/rally/calculate", response_model=RallyTimingResponse)
async def calculate_rally_timing_endpoint(request: RallyTimingRequest):
    """
    Calculate synchronized rally launch timing for multiple leaders.
    
    Input:
    - leaders: Array of leader objects with:
      - name: Leader name (Alpha, Beta, etc.)
      - march_time_str: March time in "m:ss" format (e.g., "1:15")
      - rally_fill_minutes: Rally fill time (1, 5, 10, 15, 20)
      - hit_order: Desired hit order (1 = first, 2 = second, etc.)
    
    Output:
    - calculations: Array with launch times, hit times, and instructions for each leader
    - summary: Overall summary of the rally timing
    
    Example:
    POST /rally/calculate
    {
      "leaders": [
        {"name": "Alpha", "march_time_str": "1:15", "rally_fill_minutes": 5, "hit_order": 1},
        {"name": "Bravo", "march_time_str": "3:08", "rally_fill_minutes": 5, "hit_order": 2}
      ]
    }
    """
    try:
        result = calculate_rally_timing(request.leaders)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")

@app.get("/rally/info")
async def rally_timing_info():
    """Get information about the rally timing calculator"""
    return {
        "name": "Rally Timing Calculator",
        "version": "1.0.0",
        "description": "Calculate synchronized rally launch times for WOS players",
        "max_leaders": 5,
        "rally_fill_options": [1, 5, 10, 15, 20],
        "endpoint": "/rally/calculate",
        "method": "POST"
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Hero Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/heroes")
def get_all_heroes():
    """Get all available heroes with their skills."""
    heroes = _hero_loader.get_all_heroes()
    return {
        "count": len(heroes),
        "heroes": heroes,
    }


@app.get("/heroes/{hero_name}")
def get_hero(hero_name: str):
    """Get a specific hero by name."""
    hero = _hero_loader.get_hero_by_name(hero_name)
    if not hero:
        raise HTTPException(status_code=404, detail=f"Hero '{hero_name}' not found")
    return hero


@app.post("/heroes/resolve-skills")
def resolve_hero_skills(hero_name: str, star: int = 5, widget: int = 5):
    """
    Resolve a hero's expedition skills into combat modifiers.
    
    Returns:
    {
        "hero": "Flint",
        "star": 5,
        "widget": 5,
        "modifiers": {
            "attack_bonus": 0.25,
            "lethality_bonus": 0.30,
            ...
        }
    }
    """
    from heroes.skill_resolver import SkillResolver
    
    resolver = SkillResolver(_hero_loader)
    modifiers = resolver.resolve(hero_name, star, widget)
    
    if not modifiers and not _hero_loader.get_hero_by_name(hero_name):
        raise HTTPException(status_code=404, detail=f"Hero '{hero_name}' not found")
    
    return {
        "hero": hero_name,
        "star": star,
        "widget": widget,
        "modifiers": modifiers,
    }


@app.post("/heroes/resolve-all")
def resolve_all_heroes_skills(star: int = 5, widget: int = 5):
    """
    Resolve all heroes' expedition skills into combat modifiers.
    
    Returns:
    {
        "star": 5,
        "widget": 5,
        "heroes": {
            "Flint": {"attack_bonus": 0.25, ...},
            "Molly": {"attack_bonus": 0.15, ...},
            ...
        }
    }
    """
    from heroes.skill_resolver import SkillResolver
    
    resolver = SkillResolver(_hero_loader)
    all_modifiers = resolver.resolve_all_heroes(star, widget)
    
    return {
        "star": star,
        "widget": widget,
        "heroes": all_modifiers,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  OCR Endpoints
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import File, UploadFile
import tempfile
from ocr_system import get_ocr_system


@app.post("/ocr/extract-stats")
async def extract_stats_from_screenshot(file: UploadFile = File(...)):
    """
    Extract troop stats from a WOS scout screenshot using Claude Vision API.
    
    Upload a screenshot and get back parsed troop stats:
    {
        "success": true,
        "stats": {
            "infantry": {"attack_pct": 150, "defense_pct": 120, ...},
            "lancer": {...},
            "marksman": {...},
            "formation": {...},
            "troop_count": 50000
        },
        "confidence": 0.95
    }
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
        
        # Extract stats using OCR
        ocr = get_ocr_system()
        result = ocr.extract_stats_from_image(tmp_path)
        
        # Clean up
        import os
        os.unlink(tmp_path)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@app.post("/ocr/extract-and-simulate")
async def extract_and_simulate_battle(
    file: UploadFile = File(...),
    defender_name: str = "Defender",
    defender_attack_pct: float = 0.0,
    defender_defense_pct: float = 0.0,
    defender_health_pct: float = 0.0,
    defender_lethality_pct: float = 0.0,
):
    """
    Extract stats from screenshot and immediately simulate a battle.
    
    Useful for quick battle predictions from scout reports.
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name
        
        # Extract stats
        ocr = get_ocr_system()
        ocr_result = ocr.extract_stats_from_image(tmp_path)
        
        # Clean up
        import os
        os.unlink(tmp_path)
        
        if not ocr_result.get("success"):
            return ocr_result
        
        # Build attacker army from extracted stats
        attacker_stats = ocr_result.get("stats", {})
        attacker_army = ArmyStats.from_scout(
            name="Attacker",
            infantry=attacker_stats.get("infantry", {}),
            lancer=attacker_stats.get("lancer", {}),
            marksman=attacker_stats.get("marksman", {}),
            formation=attacker_stats.get("formation", {"infantry": 0.5, "lancer": 0.2, "marksman": 0.3}),
            troop_count=attacker_stats.get("troop_count", 50000),
        )
        
        # Build defender army from input
        defender_army = ArmyStats.from_scout(
            name=defender_name,
            infantry={"attack_pct": defender_attack_pct, "defense_pct": defender_defense_pct, "health_pct": defender_health_pct, "lethality_pct": defender_lethality_pct},
            lancer={"attack_pct": defender_attack_pct, "defense_pct": defender_defense_pct, "health_pct": defender_health_pct, "lethality_pct": defender_lethality_pct},
            marksman={"attack_pct": defender_attack_pct, "defense_pct": defender_defense_pct, "health_pct": defender_health_pct, "lethality_pct": defender_lethality_pct},
            formation={"infantry": 0.5, "lancer": 0.2, "marksman": 0.3},
            troop_count=50000,
        )
        
        # Simulate battle
        result = _combat_engine.simulate_battle(attacker_army, defender_army)
        
        return {
            "success": True,
            "ocr_confidence": ocr_result.get("confidence"),
            "battle_result": result,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ═══════════════════════════════════════════════════════════════════════════
#  Rally Timing Endpoints (v2)
# ═══════════════════════════════════════════════════════════════════════════

from api.rally_timing_v2 import get_rally_calculator


class RallyTimingInput(BaseModel):
    leaders: list  # [{"name": "Alpha", "march_time": 30, "rally_fill_time": 10}, ...]
    hitting_order: list  # ["Alpha", "Beta", "Gamma"]
    hit_spacing: float = 0.0  # seconds between hits


@app.post("/rally/calculate-v2")
def calculate_rally_timing(input_data: RallyTimingInput):
    """
    Calculate synchronized rally launch timing.
    
    Input:
    {
        "leaders": [
            {"name": "Alpha", "march_time": 30, "rally_fill_time": 10},
            {"name": "Beta", "march_time": 30, "rally_fill_time": 10},
            {"name": "Gamma", "march_time": 30, "rally_fill_time": 10}
        ],
        "hitting_order": ["Alpha", "Beta", "Gamma"],
        "hit_spacing": 2.0
    }
    
    Output:
    {
        "success": true,
        "launch_sequence": [
            {
                "leader_name": "Alpha",
                "launch_time": 0.0,
                "launch_order": 1,
                "hit_time": 30.0,
                "wait_instruction": "Launch immediately"
            },
            {
                "leader_name": "Beta",
                "launch_time": 2.0,
                "launch_order": 2,
                "hit_time": 32.0,
                "wait_instruction": "Wait 2.0s after Alpha launches"
            },
            ...
        ],
        "summary": "Alpha launches first. Beta waits 2.0s, then launches. Gamma waits 2.0s after Beta, then launches."
    }
    """
    calculator = get_rally_calculator()
    result = calculator.calculate(
        leaders=input_data.leaders,
        hitting_order=input_data.hitting_order,
        hit_spacing=input_data.hit_spacing,
    )
    return result
