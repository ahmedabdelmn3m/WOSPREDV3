"""
BattleSimulator — runs a complete round-based battle between two ArmyStats objects.

Rules (matches spec):
- Both sides strike simultaneously each round.
- Battle ends when one side hits 0 troops, OR max_rounds is reached.
- Deep copies are used — original ArmyStats objects are never mutated.
- simulate_full() returns the complete result dict used by the API.
"""

import copy
from typing import List, Tuple

from .troop_stats import ArmyStats
from .turn_resolver import TurnResolver


class BattleSimulator:

    def __init__(
        self,
        casualty_rate: float = 0.05,
        skill_engine=None,
    ):
        self.resolver = TurnResolver(
            casualty_rate=casualty_rate,
            skill_engine=skill_engine,
        )

    # ─────────────────────────────────────────────────────────────────────
    #  Core simulation loop
    # ─────────────────────────────────────────────────────────────────────

    def simulate(
        self,
        attacker: ArmyStats,
        defender: ArmyStats,
        max_rounds: int = 20,
    ) -> Tuple[str, List[dict]]:
        """
        Run the battle.  Returns (winner, round_history).
        winner ∈ { "attacker", "defender", "draw" }
        """
        # Work on deep copies — never mutate the caller's data
        atk = copy.deepcopy(attacker)
        dfn = copy.deepcopy(defender)

        history: List[dict] = []

        for round_num in range(1, max_rounds + 1):
            # Snapshot troop counts BEFORE the round fires
            # (combat is simultaneous — both strikes land even if one side dies)
            atk_before = atk.troop_count
            dfn_before = dfn.troop_count

            round_result = self.resolver.resolve_turn(atk, dfn, round_num)
            history.append(round_result)

            # ── Elimination checks ────────────────────────────────────────
            both_dead = atk.troop_count <= 0 and dfn.troop_count <= 0
            if both_dead:
                # Simultaneous elimination → whoever started the round with
                # more troops "wins" (they inflicted the killing blow first)
                winner = "attacker" if atk_before >= dfn_before else "defender"
                return winner, history

            if dfn.troop_count <= 0:
                return "attacker", history

            if atk.troop_count <= 0:
                return "defender", history

        # ── Max rounds hit — compare survivors ───────────────────────────
        if atk.troop_count > dfn.troop_count:
            return "attacker", history
        elif dfn.troop_count > atk.troop_count:
            return "defender", history
        else:
            return "draw", history

    # ─────────────────────────────────────────────────────────────────────
    #  Full result (used by CombatEngine / API)
    # ─────────────────────────────────────────────────────────────────────

    def simulate_full(
        self,
        attacker: ArmyStats,
        defender: ArmyStats,
        max_rounds: int = 20,
    ) -> dict:
        """
        Run simulation and return a complete structured result.

        Includes:
        - Winner
        - Rounds played
        - Initial vs surviving troops per side
        - Total casualties + loss rate per side
        - Army damage / defense summary
        - Full round-by-round history
        """
        atk_initial = attacker.troop_count
        dfn_initial = defender.troop_count

        winner, history = self.simulate(attacker, defender, max_rounds)

        # Pull final troop counts from last round in history
        last = history[-1] if history else {}
        atk_remaining = last.get("attacker", {}).get("remaining", atk_initial)
        dfn_remaining = last.get("defender", {}).get("remaining", dfn_initial)

        # Sum casualties across all rounds
        atk_casualties = sum(r["attacker"]["casualties"] for r in history)
        dfn_casualties = sum(r["defender"]["casualties"] for r in history)

        return {
            "winner":        winner,
            "rounds_played": len(history),
            "attacker": {
                "name":           attacker.name,
                "initial_troops": atk_initial,
                "survivors":      atk_remaining,
                "casualties":     atk_casualties,
                "loss_rate":      round(atk_casualties / atk_initial, 4) if atk_initial else 0,
                "army_damage":    round(attacker.army_damage(),  8),
                "army_defense":   round(attacker.army_defense(), 8),
                "stat_breakdown": attacker.stat_summary(),
            },
            "defender": {
                "name":           defender.name,
                "initial_troops": dfn_initial,
                "survivors":      dfn_remaining,
                "casualties":     dfn_casualties,
                "loss_rate":      round(dfn_casualties / dfn_initial, 4) if dfn_initial else 0,
                "army_damage":    round(defender.army_damage(),  8),
                "army_defense":   round(defender.army_defense(), 8),
                "stat_breakdown": defender.stat_summary(),
            },
            "history": history,
        }
