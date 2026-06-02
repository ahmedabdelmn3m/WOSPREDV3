from core_engine.combat_engine import CombatEngine

class V1RawModel:
    def __init__(self, skill_engine=None):
        self.engine = CombatEngine(skill_engine)

    def predict(self, attacker, defender):
        return self.engine.run_battle(attacker, defender)
