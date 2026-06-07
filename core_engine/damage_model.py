"""
Verified Damage Formula (Source: WOS community research + screenshot confirmation):

    damage = (attack × (1 + Σ attack stats) × lethality × (1 + Σ lethality stats)) / 100

The / 100 keeps numbers manageable after multiplicative stacking.
Previous repo version had this INVERTED as 100 / (...) — now corrected.
"""


class DamageModel:
    """
    Calculates damage power for one troop type.

    Parameters
    ----------
    attack          : Base attack value. Use 1.0 when only % bonuses are
                      known (e.g. from a scout screenshot).
    attack_bonus    : Σ attack bonuses in DECIMAL form.
                      150 % → 1.50   |   200 % → 2.00
    lethality       : Base lethality value (same rule as attack).
    lethality_bonus : Σ lethality bonuses in decimal form.
    """

    @staticmethod
    def calculate(
        attack: float,
        attack_bonus: float,
        lethality: float,
        lethality_bonus: float,
    ) -> float:
        """
        damage = (attack × (1 + attack_bonus) × lethality × (1 + lethality_bonus)) / 100
        """
        return (
            attack    * (1.0 + attack_bonus) *
            lethality * (1.0 + lethality_bonus)
        ) / 100.0

    # ── Legacy alias — keeps old call-sites working ─────────────────────
    @staticmethod
    def calculate_damage(
        attack: float,
        attack_stats_sum: float,
        lethality: float,
        lethality_stats_sum: float,
    ) -> float:
        return DamageModel.calculate(
            attack, attack_stats_sum,
            lethality, lethality_stats_sum,
        )
