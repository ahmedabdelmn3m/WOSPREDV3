"""
FormationOptimizer — tests standard WOS formations and ranks them.

Given own stats and an enemy scout, runs the full battle for each
formation in TEST_FORMATIONS and returns results sorted by:
  1. Win first
  2. Win probability descending
  3. Attacker loss rate ascending (fewer losses = better)
"""

from __future__ import annotations

import copy
from .troop_stats import ArmyStats, Formation
from .combat_engine import CombatEngine

# Standard formations to test: (infantry%, lancer%, marksman%)
TEST_FORMATIONS: list[tuple[int, int, int]] = [
    (50, 20, 30),   # Balanced (default)
    (60, 10, 30),   # Infantry-heavy
    (40, 30, 30),   # Lancer-boost
    (70, 10, 20),   # Infantry dominant
    (40, 20, 40),   # Marksman-heavy
    (33, 34, 33),   # Equal thirds
    (20, 10, 70),   # Marksman dominant
    (50, 30, 20),   # Infantry + Lancer
    (30, 30, 40),   # Lancer + Marksman
    (60, 20, 20),   # Infantry + even split
    (20, 30, 50),   # Marksman + Lancer
    (80, 10, 10),   # Pure infantry
    (10, 80, 10),   # Pure lancer
    (10, 10, 80),   # Pure marksman
]


class FormationOptimizer:

    def __init__(self, engine: CombatEngine):
        self.engine = engine

    # ─────────────────────────────────────────────────────────────────────
    #  Public
    # ─────────────────────────────────────────────────────────────────────

    def optimize(
        self,
        own_army:   ArmyStats,
        enemy_army: ArmyStats,
        max_rounds: int = 20,
    ) -> dict:
        """
        Test all formations and return ranked results.
        """
        results = []

        for inf_pct, lan_pct, mrk_pct in TEST_FORMATIONS:
            test = copy.deepcopy(own_army)
            test.formation = Formation(
                infantry=inf_pct / 100.0,
                lancer=lan_pct   / 100.0,
                marksman=mrk_pct / 100.0,
            )

            battle   = self.engine.run_battle(test, enemy_army, max_rounds)
            win_prob = self._win_prob(battle)

            results.append({
                "formation": {
                    "infantry_pct":  inf_pct,
                    "lancer_pct":    lan_pct,
                    "marksman_pct":  mrk_pct,
                },
                "label":              f"{inf_pct}/{lan_pct}/{mrk_pct}",
                "winner":             battle["winner"],
                "win_probability":    round(win_prob, 4),
                "rounds_played":      battle["rounds_played"],
                "attacker_survivors": battle["attacker"]["survivors"],
                "attacker_casualties":battle["attacker"]["casualties"],
                "attacker_loss_rate": battle["attacker"]["loss_rate"],
                "defender_survivors": battle["defender"]["survivors"],
            })

        # Sort: wins first, then best probability, then fewest losses
        results.sort(
            key=lambda r: (
                1 if r["winner"] == "attacker" else 0,
                r["win_probability"],
                -r["attacker_loss_rate"],
            ),
            reverse=True,
        )

        winning  = [r for r in results if r["winner"] == "attacker"]
        losing   = [r for r in results if r["winner"] != "attacker"]
        best     = results[0] if results else None

        return {
            "best_formation":       best["formation"]       if best else None,
            "best_label":           best["label"]           if best else None,
            "best_win_probability": best["win_probability"] if best else 0,
            "winning_count":        len(winning),
            "losing_count":         len(losing),
            "all_results":          results,
            "winning_formations":   winning,
            "losing_formations":    losing,
        }

    # ─────────────────────────────────────────────────────────────────────
    #  Utility
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _win_prob(battle: dict) -> float:
        winner = battle["winner"]
        atk    = battle["attacker"]
        dfn    = battle["defender"]
        if winner == "attacker":
            s = atk["survivors"] / atk["initial_troops"] if atk["initial_troops"] else 0
            return 0.50 + 0.50 * s
        elif winner == "defender":
            s = dfn["survivors"] / dfn["initial_troops"] if dfn["initial_troops"] else 0
            return 0.50 - 0.50 * s
        return 0.50
