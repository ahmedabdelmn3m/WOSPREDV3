"""
CombatEngine — main entry point for the V1 Deterministic Combat Engine.

Verified formulas used throughout:
    damage  = (attack × (1 + Σ attack_bonus)  × lethality × (1 + Σ lethality_bonus)) / 100
    defense = (defense × (1 + Σ defense_bonus) × health   × (1 + Σ health_bonus))    / 100
"""

from .battle_simulator import BattleSimulator
from .troop_stats import ArmyStats


class CombatEngine:

    def __init__(
        self,
        casualty_rate: float = 0.05,
        skill_engine=None,
    ):
        self.simulator = BattleSimulator(
            casualty_rate=casualty_rate,
            skill_engine=skill_engine,
        )

    def run_battle(
        self,
        attacker: ArmyStats,
        defender: ArmyStats,
        max_rounds: int = 20,
    ) -> dict:
        """
        Run a complete battle simulation.

        Parameters
        ----------
        attacker   : ArmyStats object for the attacking force.
        defender   : ArmyStats object for the defending force.
        max_rounds : Battle is declared a draw if no one is eliminated by this round.

        Returns
        -------
        Full simulation result dict (winner, survivors, casualties, history).
        """
        return self.simulator.simulate_full(attacker, defender, max_rounds)
