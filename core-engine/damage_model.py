class DamageModel:
    @staticmethod
    def calculate_damage(attack, attack_stats_sum, lethality, lethality_stats_sum):
        """
        Damage = 100 / (Attack * (1 + ΣAttackStats) * Lethality * (1 + ΣLethalityStats))
        Wait, the formula in the prompt seems to be for a 'damage factor' or something similar 
        since it has 100 / (...). Let's implement as specified.
        """
        denominator = (attack * (1 + attack_stats_sum) * lethality * (1 + lethality_stats_sum))
        if denominator == 0:
            return 0
        return 100 / denominator
