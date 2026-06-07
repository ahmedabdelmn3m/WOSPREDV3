"""
V2CalibratedModel — wraps V1 result with a sigmoid probability estimate.

This is a placeholder model.  Weights are un-calibrated defaults.
Real calibration happens in the V2 Learning Engine (ai_calibration/) once
battle report data is collected.

Feature used: damage advantage ratio
    feature = (atk_dmg / def_def) - (def_dmg / atk_def)
    Positive → attacker has the edge.  Negative → defender has the edge.

Win probability formula:
    z     = v1_score × W1  +  feature × W2  +  bias
    P(win) = sigmoid(z)

v1_score: +1 (attacker wins V1), 0 (draw), -1 (defender wins V1)
"""

import math
from core_engine.troop_stats import ArmyStats


class V2CalibratedModel:

    def __init__(self, v1_model, weights: dict = None):
        self.v1_model = v1_model
        # Default weights — UNVERIFIED, will be overwritten by learning engine
        self.weights = weights or {
            "w1":   1.0,   # weight on V1 binary outcome
            "w2":   0.5,   # weight on damage-advantage feature
            "bias": 0.0,
        }

    # ─────────────────────────────────────────────────────────────────────

    def predict_outcome(
        self,
        attacker: ArmyStats,
        defender: ArmyStats,
        max_rounds: int = 20,
    ) -> dict:
        """
        Run V1 simulation then layer a calibrated win probability on top.
        """
        v1_result = self.v1_model.predict(attacker, defender, max_rounds)

        # Feature: damage advantage
        atk_dmg = attacker.army_damage()
        def_dmg = defender.army_damage()
        atk_def = attacker.army_defense()
        def_def = defender.army_defense()

        dmg_advantage = 0.0
        if def_def > 0 and atk_def > 0:
            dmg_advantage = (atk_dmg / def_def) - (def_dmg / atk_def)

        # V1 score: +1 / 0 / -1
        v1_map = {"attacker": 1.0, "draw": 0.0, "defender": -1.0}
        v1_score = v1_map.get(v1_result.get("winner", "draw"), 0.0)

        # Sigmoid on weighted sum
        z = (
            v1_score      * self.weights["w1"] +
            dmg_advantage * self.weights["w2"] +
            self.weights["bias"]
        )
        win_probability = self._sigmoid(z)

        return {
            "v1_result":       v1_result,
            "win_probability": round(win_probability, 4),
            "predicted_winner": "attacker" if win_probability > 0.5 else "defender",
            "features": {
                "v1_score":       v1_score,
                "dmg_advantage":  round(dmg_advantage, 6),
            },
            "calibration_note": (
                "UNVERIFIED — V2 weights are defaults. "
                "Accuracy improves as battle reports are submitted."
            ),
        }

    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))
