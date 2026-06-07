"""
PredictionEngine — wraps CombatEngine with intelligence analysis.

Adds on top of raw simulation:
- Win probability (0.0 → 1.0) derived from survivor ratio
- Per-troop-type strength/weakness analysis
- Bottleneck detection (which stat is holding you back most)
- Plain-English battle summary
"""

from __future__ import annotations

import copy
from .troop_stats import ArmyStats
from .combat_engine import CombatEngine

TROOP_TYPES = ["infantry", "lancer", "marksman"]
STAT_FIELDS  = ["attack_bonus", "lethality_bonus", "defense_bonus", "health_bonus"]
STAT_LABELS  = {
    "attack_bonus":    "Attack%",
    "lethality_bonus": "Lethality%",
    "defense_bonus":   "Defense%",
    "health_bonus":    "Health%",
}


class PredictionEngine:

    def __init__(self, engine: CombatEngine):
        self.engine = engine

    # ─────────────────────────────────────────────────────────────────────
    #  Public
    # ─────────────────────────────────────────────────────────────────────

    def predict(
        self,
        attacker: ArmyStats,
        defender: ArmyStats,
        max_rounds: int = 20,
    ) -> dict:
        """
        Full prediction.  Returns everything the UI needs:
        - V1 simulation result (winner, history, survivors …)
        - win_probability
        - strength_analysis (per troop type)
        - bottleneck (which stat to upgrade first)
        - summary (plain English)
        """
        battle = self.engine.run_battle(attacker, defender, max_rounds)
        win_prob = self._win_probability(battle)

        return {
            **battle,
            "win_probability":   win_prob,
            "strength_analysis": self._matchup_analysis(attacker, defender),
            "bottleneck":        self._find_bottleneck(attacker, defender, win_prob),
            "summary":           self._summary(battle, win_prob),
        }

    # ─────────────────────────────────────────────────────────────────────
    #  Win probability
    # ─────────────────────────────────────────────────────────────────────

    def _win_probability(self, battle: dict) -> float:
        """
        Derive win probability from survivor ratio.
        A win where 90 % of your troops survive ≈ 95 % prob.
        A win where 5 % survive ≈ 53 % prob.
        A loss mirrors this on the defender side.
        """
        winner = battle["winner"]
        atk    = battle["attacker"]
        dfn    = battle["defender"]

        if winner == "attacker":
            survival = atk["survivors"] / atk["initial_troops"] if atk["initial_troops"] else 0
            return round(0.50 + 0.50 * survival, 4)
        elif winner == "defender":
            survival = dfn["survivors"] / dfn["initial_troops"] if dfn["initial_troops"] else 0
            return round(0.50 - 0.50 * survival, 4)
        return 0.50   # draw

    # ─────────────────────────────────────────────────────────────────────
    #  Per-troop-type analysis
    # ─────────────────────────────────────────────────────────────────────

    def _matchup_analysis(self, attacker: ArmyStats, defender: ArmyStats) -> dict:
        """
        Compare attacker's damage penetration vs defender's for each troop type.

        penetration = troop_damage / opposing_troop_defense
        net_advantage = attacker_penetration / defender_penetration

        Status bands:
        ≥ 1.50 → DOMINANT
        ≥ 1.10 → ADVANTAGE
        ≥ 0.90 → EVEN
        ≥ 0.60 → DISADVANTAGE
         < 0.60 → CRITICAL
        """
        analysis = {}

        for t in TROOP_TYPES:
            atk_t = getattr(attacker, t)
            def_t = getattr(defender, t)

            atk_pen = (atk_t.effective_damage  / def_t.effective_defense
                       if def_t.effective_defense > 0 else float("inf"))
            def_pen = (def_t.effective_damage  / atk_t.effective_defense
                       if atk_t.effective_defense > 0 else float("inf"))

            net = atk_pen / def_pen if def_pen > 0 else float("inf")

            if   net >= 1.50: status = "DOMINANT"
            elif net >= 1.10: status = "ADVANTAGE"
            elif net >= 0.90: status = "EVEN"
            elif net >= 0.60: status = "DISADVANTAGE"
            else:              status = "CRITICAL"

            analysis[t] = {
                "atk_penetration": round(atk_pen, 4),
                "def_penetration": round(def_pen, 4),
                "net_advantage":   round(net,     4),
                "status":          status,
            }

        return analysis

    # ─────────────────────────────────────────────────────────────────────
    #  Bottleneck detection
    # ─────────────────────────────────────────────────────────────────────

    def _find_bottleneck(
        self,
        attacker: ArmyStats,
        defender: ArmyStats,
        base_win_prob: float,
    ) -> dict:
        """
        Test which stat, if increased by +50 %, improves win probability most.
        Only runs when base_win_prob < 0.90 (no point if you're already dominant).
        """
        if base_win_prob >= 0.90:
            return {"message": "No critical weakness — army is dominant."}

        best_gain  = 0.0
        bottleneck = {}

        for t in TROOP_TYPES:
            for stat in STAT_FIELDS:
                test_atk   = copy.deepcopy(attacker)
                troop      = getattr(test_atk, t)
                current    = getattr(troop, stat)
                setattr(troop, stat, current + 0.50)   # +50 % test

                result   = self.engine.run_battle(test_atk, defender)
                new_prob = self._win_probability(result)
                gain     = new_prob - base_win_prob

                if gain > best_gain:
                    best_gain  = gain
                    bottleneck = {
                        "troop_type":          t,
                        "stat":                STAT_LABELS[stat],
                        "current_pct":         round(current * 100, 1),
                        "win_gain_per_50pct":  round(gain * 100, 1),
                        "recommendation":      (
                            f"Increasing {t.title()} {STAT_LABELS[stat]} "
                            f"by 50 % would raise your win chance "
                            f"by ~{round(gain * 100, 1)} pp."
                        ),
                    }

        return bottleneck or {"message": "All stat improvements have similar impact."}

    # ─────────────────────────────────────────────────────────────────────
    #  Plain-English summary
    # ─────────────────────────────────────────────────────────────────────

    def _summary(self, battle: dict, win_prob: float) -> str:
        winner = battle["winner"]
        rounds = battle["rounds_played"]
        atk    = battle["attacker"]
        dfn    = battle["defender"]
        pct    = round(win_prob * 100, 1)

        if winner == "attacker":
            surv = round(atk["survivors"] / atk["initial_troops"] * 100, 1) if atk["initial_troops"] else 0
            return (
                f"{atk['name']} wins in {rounds} rounds. "
                f"{surv} % of troops survive. "
                f"Win probability: {pct} %."
            )
        elif winner == "defender":
            surv = round(dfn["survivors"] / dfn["initial_troops"] * 100, 1) if dfn["initial_troops"] else 0
            return (
                f"{dfn['name']} wins in {rounds} rounds. "
                f"Enemy retains {surv} % troops. "
                f"Your win probability: {pct} %."
            )
        return f"Battle draws after {rounds} rounds. Win probability: 50 %."
