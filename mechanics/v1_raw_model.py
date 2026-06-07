from core_engine.combat_engine import CombatEngine
from core_engine.troop_stats import ArmyStats


class V1RawModel:
    """
    V1 Deterministic prediction layer.
    Thin wrapper around CombatEngine — returns the raw simulation result.
    """

    def __init__(self, skill_engine=None, casualty_rate: float = 0.05):
        self.engine = CombatEngine(
            casualty_rate=casualty_rate,
            skill_engine=skill_engine,
        )

    def predict(
        self,
        attacker: ArmyStats,
        defender: ArmyStats,
        max_rounds: int = 20,
    ) -> dict:
        return self.engine.run_battle(attacker, defender, max_rounds)
