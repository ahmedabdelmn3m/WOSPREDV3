from .turn_resolver import TurnResolver

class BattleSimulator:
    def __init__(self, skill_engine=None):
        self.resolver = TurnResolver(skill_engine)

    def simulate(self, attacker, defender, max_rounds=20):
        history = []
        attacker['current_hp'] = attacker.get('hp', 1000) # Default HP
        defender['current_hp'] = defender.get('hp', 1000)

        for r in range(1, max_rounds + 1):
            # Attacker hits defender
            atk_res = self.resolver.resolve_turn(attacker, defender, r)
            history.append({"side": "attacker", "result": atk_res})
            
            if defender['current_hp'] <= 0:
                return "attacker", history

            # Defender hits attacker
            def_res = self.resolver.resolve_turn(defender, attacker, r)
            history.append({"side": "defender", "result": def_res})

            if attacker['current_hp'] <= 0:
                return "defender", history

        return "draw", history
