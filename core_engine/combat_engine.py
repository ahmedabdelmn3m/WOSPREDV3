from .battle_simulator import BattleSimulator

class CombatEngine:
    """
    Main entry point for V1 Deterministic Combat Engine
    """
    def __init__(self, skill_engine=None):
        self.simulator = BattleSimulator(skill_engine)

    def run_battle(self, attacker_data, defender_data, settings=None):
        max_rounds = settings.get('max_rounds', 20) if settings else 20
        winner, history = self.simulator.simulate(attacker_data, defender_data, max_rounds)
        
        return {
            "winner": winner,
            "rounds_played": len(history) // 2,
            "history": history
        }
