class DefenseModel:
    @staticmethod
    def calculate_defense_power(defense, defense_stats_sum, health, health_stats_sum):
        """
        DefensePower = 100 * Defense * (1 + ΣDefenseStats) * Health * (1 + ΣHealthStats)
        """
        return 100 * defense * (1 + defense_stats_sum) * health * (1 + health_stats_sum)
