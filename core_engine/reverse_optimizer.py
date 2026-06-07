"""
ReverseOptimizer — answers "what do I need to win?"

Given own stats, enemy stats, and a win-probability target,
it finds the minimum increase per stat needed to reach that target,
then ranks recommendations by impact-per-stat-point (highest ROI first).
"""

from __future__ import annotations

import copy
from .troop_stats import ArmyStats
from .combat_engine import CombatEngine

TROOP_TYPES  = ["infantry", "lancer", "marksman"]
# Ordered by typical combat impact: offensive stats first
STAT_FIELDS  = ["attack_bonus", "lethality_bonus", "health_bonus", "defense_bonus"]
STAT_LABELS  = {
    "attack_bonus":    "Attack%",
    "lethality_bonus": "Lethality%",
    "defense_bonus":   "Defense%",
    "health_bonus":    "Health%",
}
MAX_INCREASE = 5.0     # 500 % cap on stat searches


class ReverseOptimizer:

    def __init__(self, engine: CombatEngine):
        self.engine = engine

    # ─────────────────────────────────────────────────────────────────────
    #  Public
    # ─────────────────────────────────────────────────────────────────────

    def optimize(
        self,
        own_army:    ArmyStats,
        enemy_army:  ArmyStats,
        target_prob: float = 0.75,
        max_rounds:  int   = 20,
    ) -> dict:
        """
        Find which stat improvements are needed to reach target_prob.
        Returns top recommendations + win paths for 75 / 85 / 95 %.
        """
        base_result  = self.engine.run_battle(own_army, enemy_army, max_rounds)
        current_prob = self._win_prob(base_result)

        if current_prob >= target_prob:
            return {
                "current_win_probability": round(current_prob, 4),
                "target_win_probability":  round(target_prob,  4),
                "already_meets_target":    True,
                "top_recommendations":     [],
                "win_paths":               {},
            }

        recs = []
        for t in TROOP_TYPES:
            for stat in STAT_FIELDS:
                needed = self._binary_search(
                    own_army, enemy_army, t, stat, target_prob, max_rounds
                )
                if needed is not None:
                    impact = self._impact_score(
                        own_army, enemy_army, t, stat, current_prob, max_rounds
                    )
                    recs.append({
                        "troop_type":          t,
                        "stat":                STAT_LABELS[stat],
                        "_stat_key":           stat,     # internal — stripped before response
                        "needed_increase_pct": round(needed, 1),
                        "impact_score":        round(impact, 4),
                        "impact_label":        self._impact_label(impact),
                        # higher ROI = higher priority
                        "_priority":           impact / max(needed, 1.0),
                    })

        # Sort: best ROI first
        recs.sort(key=lambda r: r["_priority"], reverse=True)

        # Clean internal keys
        clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in recs]

        return {
            "current_win_probability": round(current_prob, 4),
            "target_win_probability":  round(target_prob,  4),
            "already_meets_target":    False,
            "top_recommendations":     clean[:6],
            "all_recommendations":     clean,
            "win_paths":               self._win_paths(own_army, enemy_army, max_rounds),
        }

    # ─────────────────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────────────────

    def _binary_search(
        self,
        own:        ArmyStats,
        enemy:      ArmyStats,
        troop_type: str,
        stat:       str,
        target:     float,
        max_rounds: int,
        precision:  int = 20,
    ) -> float | None:
        """
        Binary-search for the minimum stat increase (decimal, e.g. 1.2 = +120 %)
        needed so that win_probability >= target.
        Returns the increase in percentage points, or None if even MAX_INCREASE isn't enough.
        """
        lo, hi = 0.0, MAX_INCREASE

        # First check if MAX_INCREASE is sufficient
        test  = self._apply(own, troop_type, stat, hi)
        if self._win_prob(self.engine.run_battle(test, enemy, max_rounds)) < target:
            return None   # can't get there even with max boost

        for _ in range(precision):
            mid  = (lo + hi) / 2.0
            test = self._apply(own, troop_type, stat, mid)
            prob = self._win_prob(self.engine.run_battle(test, enemy, max_rounds))
            if prob >= target:
                hi = mid
            else:
                lo = mid

        return round(hi * 100, 1)   # convert to pct

    def _impact_score(
        self,
        own:        ArmyStats,
        enemy:      ArmyStats,
        troop_type: str,
        stat:       str,
        base_prob:  float,
        max_rounds: int,
    ) -> float:
        """Win-probability gain from a fixed +50 % increase."""
        test     = self._apply(own, troop_type, stat, 0.50)
        new_prob = self._win_prob(self.engine.run_battle(test, enemy, max_rounds))
        return max(new_prob - base_prob, 0.0)

    def _win_paths(
        self,
        own_army:   ArmyStats,
        enemy_army: ArmyStats,
        max_rounds: int,
    ) -> dict:
        """For each target threshold, the 3 cheapest single-stat improvements."""
        paths = {}
        base_result = self.engine.run_battle(own_army, enemy_army, max_rounds)
        base_prob   = self._win_prob(base_result)

        for target in [0.75, 0.85, 0.95]:
            if base_prob >= target:
                paths[f"{int(target * 100)}pct"] = {"already_met": True}
                continue

            cheapest = []
            for t in TROOP_TYPES:
                for stat in STAT_FIELDS:
                    needed = self._binary_search(
                        own_army, enemy_army, t, stat, target, max_rounds
                    )
                    if needed is not None:
                        cheapest.append({
                            "troop_type":    t,
                            "stat":          STAT_LABELS[stat],
                            "increase_pct":  needed,
                        })

            cheapest.sort(key=lambda r: r["increase_pct"])
            paths[f"{int(target * 100)}pct"] = cheapest[:3]

        return paths

    # ─────────────────────────────────────────────────────────────────────
    #  Utility
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _apply(army: ArmyStats, troop_type: str, stat: str, delta: float) -> ArmyStats:
        """Return a deep copy of army with one stat increased by delta."""
        army_copy = copy.deepcopy(army)
        troop     = getattr(army_copy, troop_type)
        setattr(troop, stat, getattr(troop, stat) + delta)
        return army_copy

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

    @staticmethod
    def _impact_label(score: float) -> str:
        if   score >= 0.20: return "CRITICAL"
        elif score >= 0.10: return "HIGH"
        elif score >= 0.05: return "MEDIUM"
        else:               return "LOW"
