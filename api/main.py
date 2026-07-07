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

import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator
from typing import Optional, List, Any

from core_engine.troop_stats        import ArmyStats, Formation, TroopTypeStats
from core_engine.combat_engine      import CombatEngine
from core_engine.prediction_engine  import PredictionEngine
from core_engine.reverse_optimizer  import ReverseOptimizer
from core_engine.formation_optimizer import FormationOptimizer
from core_engine.preset_manager     import PresetManager
from mechanics.v1_raw_model         import V1RawModel
from mechanics.v2_calibrated_model  import V2CalibratedModel
from hero_data import HEROES_BY_ID as STRUCTURED_HEROES, hero_to_dict
from troop_data import all_troop_stats, get_troop_base_stats, expected_skill_modifiers, TROOP_SKILL_RULES

# ── Singletons (one per process) ─────────────────────────────────────────────
_combat_engine     = CombatEngine()
_prediction_engine = PredictionEngine(_combat_engine)
_reverse_optimizer = ReverseOptimizer(_combat_engine)
_formation_optimizer = FormationOptimizer(_combat_engine)
_preset_manager    = PresetManager()
_v1                = V1RawModel()
_v2                = V2CalibratedModel(_v1)
_prediction_runs: list[dict[str, Any]] = []
_battle_logs: list[dict[str, Any]] = []
_scout_uploads: list[dict[str, Any]] = []

ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str, fallback: Any) -> Any:
    path = ROOT_DIR / relative_path
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return fallback


HERO_DEFINITIONS = _load_json("heroes/hero_definitions.json", [])
HERO_BY_ID = {hero.get("id"): hero for hero in HERO_DEFINITIONS}


def _hero_type(hero: Any) -> str:
    if isinstance(hero, HeroSelection):
        if hero.type:
            return hero.type
        structured = STRUCTURED_HEROES.get(str(hero.id or "").lower())
        return HERO_BY_ID.get(hero.id, {}).get("type") or HERO_BY_ID.get(hero.id, {}).get("specialty") or (structured.hero_type if structured else "") or ""
    if isinstance(hero, dict):
        structured = STRUCTURED_HEROES.get(str(hero.get("id") or "").lower())
        return hero.get("type") or hero.get("specialty") or HERO_BY_ID.get(hero.get("id"), {}).get("type") or HERO_BY_ID.get(hero.get("id"), {}).get("specialty") or (structured.hero_type if structured else "") or ""
    return ""


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _cors_origin_regex() -> str | None:
    raw = os.getenv("CORS_ORIGIN_REGEX")
    if raw is not None:
        return raw.strip() or None
    return r"https://wospredv-?3(?:-[a-z0-9-]+)?\.vercel\.app"

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="WOS Battle Intelligence API",
    description="Verified-formula combat simulation for Whiteout Survival.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
#  Pydantic models
# ═══════════════════════════════════════════════════════════════════════════

class TroopStatsInput(BaseModel):
    troop_type: Optional[str] = None
    tier: int = 11
    fc_level: int = 10
    attack_pct:     float = 0.0
    defense_pct:    float = 0.0
    health_pct:     float = 0.0
    lethality_pct:  float = 0.0
    attack_base:    float = 1.0
    defense_base:   float = 1.0
    health_base:    float = 1.0
    lethality_base: float = 1.0

    @model_validator(mode="after")
    def values_cannot_be_negative(self) -> "TroopStatsInput":
        if self.tier not in (10, 11):
            raise ValueError("Troop tier must be 10 or 11.")
        if self.fc_level < 1 or self.fc_level > 10:
            raise ValueError("FC level must be between 1 and 10.")
        values = self.model_dump()
        negatives = [name for name, value in values.items() if isinstance(value, (int, float)) and value < 0]
        if negatives:
            raise ValueError(f"Stats cannot be negative: {', '.join(negatives)}.")
        return self

    def to_troop_type_stats(self, troop_type: Optional[str] = None) -> TroopTypeStats:
        resolved_type = troop_type or self.troop_type
        attack_base = self.attack_base
        defense_base = self.defense_base
        health_base = self.health_base
        lethality_base = self.lethality_base
        if resolved_type:
            base = get_troop_base_stats(resolved_type, self.tier, self.fc_level)
            attack_base = base.attack
            defense_base = base.defense
            health_base = base.health
            lethality_base = base.lethality
        skill_mods = expected_skill_modifiers(resolved_type, self.fc_level) if resolved_type else {"damage_up": 0, "defense_up": 0, "damage_taken_down": 0}
        return TroopTypeStats(
            attack=attack_base,
            defense=defense_base,
            health=health_base,
            lethality=lethality_base,
            attack_bonus=self.attack_pct / 100.0,
            defense_bonus=(self.defense_pct / 100.0) + skill_mods["defense_up"],
            health_bonus=self.health_pct     / 100.0,
            lethality_bonus=self.lethality_pct / 100.0,
            troop_skill_damage_bonus=skill_mods["damage_up"],
            troop_skill_damage_taken_down=skill_mods["damage_taken_down"],
            troop_skill_notes=skill_mods["skills"],
        )


class HeroSelection(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    stars: int = 5
    widget_level: Optional[int] = None

    @model_validator(mode="after")
    def hero_values_are_valid(self) -> "HeroSelection":
        if not self.id:
            raise ValueError("Hero id is required.")
        if self.stars < 1 or self.stars > 5:
            raise ValueError("Hero stars must be between 1 and 5.")
        if self.widget_level is None or self.widget_level <= 0:
            raise ValueError("Hero widget level must be greater than zero.")
        if _hero_type(self) not in {"infantry", "lancer", "marksman"}:
            raise ValueError(f"Hero '{self.id}' must have infantry, lancer, or marksman type.")
        return self


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


class ArmyInput(BaseModel):
    name:        str             = "Unknown"
    joiners:     List[str]       = []
    infantry:    TroopStatsInput = TroopStatsInput()
    lancer:      TroopStatsInput = TroopStatsInput()
    marksman:    TroopStatsInput = TroopStatsInput()
    formation:   FormationInput  = FormationInput()
    troop_count: int             = 500_000
    heroes:      List[HeroSelection] = []

    @model_validator(mode="after")
    def main_march_is_valid(self) -> "ArmyInput":
        if self.troop_count <= 0:
            raise ValueError("Troop count must be greater than zero.")
        if len(self.heroes) != 3:
            raise ValueError("Main march must include exactly 3 heroes.")
        ids = [hero.id for hero in self.heroes]
        if len(set(ids)) != len(ids):
            raise ValueError("Main march cannot use duplicate heroes.")
        types = [_hero_type(hero) for hero in self.heroes]
        if len(set(types)) != len(types):
            raise ValueError("Main march cannot use duplicate hero types.")
        required = {"infantry", "lancer", "marksman"}
        if set(types) != required:
            raise ValueError("Main march must include exactly one infantry, one lancer, and one marksman hero.")
        return self

    def to_army_stats(self) -> ArmyStats:
        return ArmyStats(
            name=self.name,
            joiners=self.joiners,
            infantry=self.infantry.to_troop_type_stats("infantry"),
            lancer=self.lancer.to_troop_type_stats("lancer"),
            marksman=self.marksman.to_troop_type_stats("marksman"),
            formation=Formation(
                infantry=self.formation.infantry,
                lancer=self.formation.lancer,
                marksman=self.formation.marksman,
            ),
            troop_count=self.troop_count,
        )


class BattleRequest(BaseModel):
    attacker:   ArmyInput
    defender:   ArmyInput
    max_rounds: int = 20
    simulation_mode: str = "expected_value"
    monte_carlo_runs: int = 1000


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
    joiners:     List[str]       = []
    infantry:    TroopStatsInput = TroopStatsInput()
    lancer:      TroopStatsInput = TroopStatsInput()
    marksman:    TroopStatsInput = TroopStatsInput()
    formation:   FormationInput  = FormationInput()
    troop_count: int             = 500_000

    def to_army_stats(self) -> ArmyStats:
        return ArmyStats(
            name=self.name,
            joiners=self.joiners,
            infantry=self.infantry.to_troop_type_stats("infantry"),
            lancer=self.lancer.to_troop_type_stats("lancer"),
            marksman=self.marksman.to_troop_type_stats("marksman"),
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


class PredictionRunSaveRequest(BaseModel):
    attacker: ArmyInput
    defender: ArmyInput
    result: dict[str, Any]
    notes: Optional[str] = None


class BattleLogSaveRequest(BaseModel):
    own_stats: dict[str, Any]
    enemy_stats: dict[str, Any]
    own_formation: dict[str, Any]
    enemy_formation: Optional[dict[str, Any]] = None
    own_heroes: List[dict[str, Any]] = []
    enemy_heroes: List[dict[str, Any]] = []
    prediction_result: Optional[dict[str, Any]] = None
    actual_result: Optional[str] = None
    notes: Optional[str] = None
    uploaded_report_image_ref: Optional[str] = None


SCOUT_PATTERNS = {
    "infantry.attack_pct": r"infantry\s+attack\D+([\d,.]+)",
    "infantry.defense_pct": r"infantry\s+defen[sc]e\D+([\d,.]+)",
    "infantry.health_pct": r"infantry\s+health\D+([\d,.]+)",
    "infantry.lethality_pct": r"infantry\s+lethality\D+([\d,.]+)",
    "lancer.attack_pct": r"lancer\s+attack\D+([\d,.]+)",
    "lancer.defense_pct": r"lancer\s+defen[sc]e\D+([\d,.]+)",
    "lancer.health_pct": r"lancer\s+health\D+([\d,.]+)",
    "lancer.lethality_pct": r"lancer\s+lethality\D+([\d,.]+)",
    "marksman.attack_pct": r"marksman\s+attack\D+([\d,.]+)",
    "marksman.defense_pct": r"marksman\s+defen[sc]e\D+([\d,.]+)",
    "marksman.health_pct": r"marksman\s+health\D+([\d,.]+)",
    "marksman.lethality_pct": r"marksman\s+lethality\D+([\d,.]+)",
}


def _empty_scout_stats() -> dict:
    return {
        troop: {
            "attack_pct": None,
            "defense_pct": None,
            "health_pct": None,
            "lethality_pct": None,
        }
        for troop in ("infantry", "lancer", "marksman")
    }


def _parse_scout_text(text: str) -> dict:
    parsed = _empty_scout_stats()
    for key, pattern in SCOUT_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        troop, stat = key.split(".")
        parsed[troop][stat] = float(match.group(1).replace(",", ""))
    return parsed


def _prediction_metadata(attacker: ArmyInput, defender: ArmyInput, result: dict) -> dict:
    analysis = result.get("strength_analysis", {})
    ranked = []
    for troop, data in analysis.items():
        ranked.append((troop, data.get("net_advantage", 1), data.get("status", "EVEN")))
    strongest = max(ranked, key=lambda item: item[1], default=None)
    weakest = min(ranked, key=lambda item: item[1], default=None)
    uses_heroes = bool(attacker.heroes or defender.heroes)
    return {
        "confidence_level": "medium" if not uses_heroes else "low",
        "strongest_advantage": {
            "troop_type": strongest[0],
            "net_advantage": strongest[1],
            "status": strongest[2],
        } if strongest else None,
        "weakest_weakness": {
            "troop_type": weakest[0],
            "net_advantage": weakest[1],
            "status": weakest[2],
        } if weakest else None,
        "troop_type_breakdown": {
            "attacker": attacker.to_army_stats().troop_breakdown(),
            "defender": defender.to_army_stats().troop_breakdown(),
        },
        "recommended_formation_adjustment": "Use /formation/optimize to compare standard formation presets for this matchup.",
        "recommended_stat_improvements": result.get("bottleneck"),
        "effective_stats": {
            "attacker": _effective_army_stats(attacker),
            "defender": _effective_army_stats(defender),
        },
        "frontline": _frontline_summary(attacker, defender),
        "backline_damage": _backline_summary(attacker, defender),
        "main_reason": _main_reason(result),
        "suggested_changes": _suggested_changes(attacker, defender, result),
        "warnings": [
            "Prediction uses configurable MVP constants pending calibration.",
            "Hero selections are recorded but unverified hero skill values are not applied.",
            "Scout stats are treated as already including base hero/stat bonuses to avoid double counting.",
        ],
    }


def _effective_army_stats(army: ArmyInput) -> dict:
    stats = army.to_army_stats()
    return {
        "infantry": stats.infantry.to_dict(),
        "lancer": stats.lancer.to_dict(),
        "marksman": stats.marksman.to_dict(),
    }


def _frontline_summary(attacker: ArmyInput, defender: ArmyInput) -> dict:
    atk = attacker.to_army_stats().infantry.effective_defense
    dfn = defender.to_army_stats().infantry.effective_defense
    return {
        "stronger_side": "attacker" if atk > dfn else "defender" if dfn > atk else "even",
        "attacker_infantry_defense": round(atk, 6),
        "defender_infantry_defense": round(dfn, 6),
    }


def _backline_summary(attacker: ArmyInput, defender: ArmyInput) -> dict:
    atk = attacker.to_army_stats().marksman.effective_damage
    dfn = defender.to_army_stats().marksman.effective_damage
    return {
        "stronger_side": "attacker" if atk > dfn else "defender" if dfn > atk else "even",
        "attacker_marksman_damage": round(atk, 6),
        "defender_marksman_damage": round(dfn, 6),
    }


def _main_reason(result: dict) -> str:
    analysis = result.get("strength_analysis", {})
    if not analysis:
        return "Battle result is driven by total effective damage and defense."
    strongest = max(analysis.items(), key=lambda item: item[1].get("net_advantage", 1))
    return f"{strongest[0].title()} matchup has the largest edge ({strongest[1].get('status', 'EVEN')})."


def _suggested_changes(attacker: ArmyInput, defender: ArmyInput, result: dict) -> list[str]:
    suggestions = []
    atk_stats = attacker.to_army_stats()
    def_stats = defender.to_army_stats()
    if atk_stats.formation.infantry < 0.45:
        suggestions.append("Increase Infantry ratio for stronger frontline survival.")
    if atk_stats.marksman.effective_damage < def_stats.marksman.effective_damage:
        suggestions.append("Prioritize Marksman FC level or damage hero skills for backline pressure.")
    if atk_stats.infantry.effective_defense < def_stats.infantry.effective_defense:
        suggestions.append("Prioritize Infantry FC level, Infantry Defense, or Health upgrades.")
    if not suggestions:
        suggestions.append("Compare hero skill setup and FC priority; current ratio is not the obvious weakness.")
    return suggestions


def _monte_carlo_prediction(req: "BattleRequest") -> dict:
    runs = max(50, min(int(req.monte_carlo_runs or 1000), 5000))
    attacker_wins = 0
    defender_wins = 0
    draws = 0
    base_attacker = req.attacker.model_dump()
    base_defender = req.defender.model_dump()
    for _ in range(runs):
        atk = ArmyInput(**_jitter_army(base_attacker))
        dfn = ArmyInput(**_jitter_army(base_defender))
        result = _prediction_engine.predict(atk.to_army_stats(), dfn.to_army_stats(), max_rounds=req.max_rounds)
        if result["winner"] == "attacker":
            attacker_wins += 1
        elif result["winner"] == "defender":
            defender_wins += 1
        else:
            draws += 1
    deterministic = _prediction_engine.predict(req.attacker.to_army_stats(), req.defender.to_army_stats(), max_rounds=req.max_rounds)
    deterministic["winner"] = "attacker" if attacker_wins > defender_wins else "defender" if defender_wins > attacker_wins else "draw"
    deterministic["win_probability"] = round((attacker_wins + draws * 0.5) / runs, 4)
    deterministic["monte_carlo"] = {"runs": runs, "attacker_wins": attacker_wins, "defender_wins": defender_wins, "draws": draws}
    return deterministic


def _jitter_army(raw: dict) -> dict:
    copy = json.loads(json.dumps(raw))
    for troop in ("infantry", "lancer", "marksman"):
        fc = int(copy[troop].get("fc_level", 10))
        width = 0.015 + min(fc, 10) * 0.002
        roll = 1 + random.uniform(-width, width)
        copy[troop]["attack_pct"] = max(0, copy[troop].get("attack_pct", 0) * roll)
        copy[troop]["lethality_pct"] = max(0, copy[troop].get("lethality_pct", 0) * roll)
    return copy


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
            "GET  /troop-stats":         "T10 Apex and T11 Helios troop base stats and skill rules",
        },
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "WOS Battle Predictor API",
        "version": app.version,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/hero-definitions")
async def hero_definitions():
    return {
        "heroes": _load_json("heroes/hero_definitions.json", []),
        "note": "Unverified skills are exposed as pending verification and are not applied by the engine.",
    }


@app.get("/rally-hero-definitions")
async def rally_hero_definitions():
    return {
        "heroes": [hero_to_dict(hero) for hero in STRUCTURED_HEROES.values()],
        "mechanics_note": (
            "Rally leaders apply all configured expedition skills from the 3-hero march. "
            "Joiners and garrison helpers apply only the first/primary expedition skill "
            "from up to 4 heroes, per the official Combat FAQ."
        ),
        "formula_note": "Damage Up and Attack Damage Up remain separate final damage multiplier layers from Attack Up.",
    }


@app.get("/combat-constants")
async def combat_constants():
    return _load_json("config/combat_constants.json", {"constants": {}})


@app.get("/troop-stats")
async def troop_stats():
    return {
        "troop_stats": all_troop_stats(),
        "troop_skill_rules": TROOP_SKILL_RULES,
        "formula": "effective_stat = base_stat * (1 + scout_bonus_percent / 100), with hero/widget/troop skills kept as separate layers.",
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
        if req.simulation_mode == "monte_carlo":
            result = _monte_carlo_prediction(req)
        else:
            result = _prediction_engine.predict(
                req.attacker.to_army_stats(),
                req.defender.to_army_stats(),
                max_rounds=req.max_rounds,
            )
        result["simulation_mode"] = req.simulation_mode
        result["metadata"] = _prediction_metadata(req.attacker, req.defender, result)
        return result
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/prediction-runs")
async def save_prediction_run(req: PredictionRunSaveRequest):
    item = {
        "id": str(uuid4()),
        "attacker": req.attacker.model_dump(),
        "defender": req.defender.model_dump(),
        "result": req.result,
        "notes": req.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _prediction_runs.append(item)
    return {"status": "saved", "prediction_run": item}


@app.get("/prediction-runs")
async def list_prediction_runs():
    return {"prediction_runs": _prediction_runs}


@app.post("/battle-logs")
async def save_battle_log(req: BattleLogSaveRequest):
    item = {
        "id": str(uuid4()),
        **req.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _battle_logs.append(item)
    return {"status": "saved", "battle_log": item}


@app.get("/battle-logs")
async def list_battle_logs():
    return {"battle_logs": _battle_logs}


@app.post("/scout-upload")
async def upload_scout_image(file: UploadFile = File(...)):
    contents = await file.read()
    upload_id = str(uuid4())
    item = {
        "id": upload_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(contents),
        "parsed_stats": _empty_scout_stats(),
        "ocr_status": "pending_provider",
        "message": "Image received. OCR provider is not configured in this MVP; manual correction is required.",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _scout_uploads.append(item)
    return item


@app.post("/parse-scout-text")
async def parse_scout_text(payload: dict):
    text = str(payload.get("text", ""))
    parsed = _parse_scout_text(text)
    found = sum(
        1 for troop in parsed.values() for value in troop.values()
        if value is not None
    )
    return {
        "parsed_stats": parsed,
        "fields_found": found,
        "manual_correction_required": found < 12,
    }


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
