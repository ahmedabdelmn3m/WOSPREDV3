"""
Verified Defense Formula (Source: WOS community research + screenshot confirmation):

    defense = (defense × (1 + Σ defense stats) × health × (1 + Σ health stats)) / 100

Mirrors the damage formula structure. Previous repo had 100 × (...) — now corrected.
"""


class DefenseModel:
    """
    Calculates defense power for one troop type.

    Parameters
    ----------
    defense         : Base defense value. Use 1.0 when only % bonuses are
                      known (e.g. from a scout screenshot).
    defense_bonus   : Σ defense bonuses in DECIMAL form.
                      120 % → 1.20
    health          : Base health value (same rule as defense).
    health_bonus    : Σ health bonuses in decimal form.
    """

    @staticmethod
    def calculate(
        defense: float,
        defense_bonus: float,
        health: float,
        health_bonus: float,
    ) -> float:
        """
        defense = (defense × (1 + defense_bonus) × health × (1 + health_bonus)) / 100
        """
        return (
            defense * (1.0 + defense_bonus) *
            health  * (1.0 + health_bonus)
        ) / 100.0

    # ── Legacy alias — keeps old call-sites working ─────────────────────
    @staticmethod
    def calculate_defense_power(
        defense: float,
        defense_stats_sum: float,
        health: float,
        health_stats_sum: float,
    ) -> float:
        return DefenseModel.calculate(
            defense, defense_stats_sum,
            health, health_stats_sum,
        )
