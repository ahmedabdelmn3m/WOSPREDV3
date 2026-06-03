from .damage_model import DamageModel
from .defense_model import DefenseModel

class TurnResolver:
    def __init__(self, skill_engine=None):
        self.skill_engine = skill_engine

    def resolve_turn(self, attacker, defender, round_number):
        # Apply on_round_start skills
        if self.skill_engine:
            self.skill_engine.trigger("on_round_start", attacker, defender, round_number)

        # Calculate base damage
        raw_damage = DamageModel.calculate_damage(
            attacker['stats']['attack'],
            attacker['stats']['attack_stats_sum'],
            attacker['stats']['lethality'],
            attacker['stats']['lethality_stats_sum']
        )
        
        # Calculate defense power
        def_power = DefenseModel.calculate_defense_power(
            defender['stats']['defense'],
            defender['stats']['defense_stats_sum'],
            defender['stats']['health'],
            defender['stats']['health_stats_sum']
        )

        # Final damage calculation (simplified for engine logic)
        # Note: In a real simulation, damage would reduce health/power
        # Based on prompt: final_damage = V1_damage * skill_modifiers
        skill_modifiers = 1.0
        if self.skill_engine:
            skill_modifiers = self.skill_engine.get_modifiers(attacker, "damage")

        final_damage = raw_damage * skill_modifiers
        
        # Apply damage to defender
        defender['current_hp'] -= final_damage
        
        return {
            "round": round_number,
            "damage_dealt": final_damage,
            "defender_remaining_hp": defender['current_hp']
        }
