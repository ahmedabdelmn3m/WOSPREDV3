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

    @staticmethod
    def calculate_with_layers(
        attack: float,
        attack_bonus: float,
        lethality: float,
        lethality_bonus: float,
        damage_up: float = 0.0,
        attack_damage_up: float = 0.0,
        damage_taken_down: float = 0.0,
    ) -> float:
        """
        Transparent layered model:

        base_damage = existing attack/lethality formula
        final_damage = base_damage * (1 + damage_up + attack_damage_up)
        final_incoming_damage = final_damage * (1 - damage_taken_down)

        This is a configurable layer separation, not a claim of exact hidden
        Whiteout Survival formula precision.
        """
        base_damage = DamageModel.calculate(
            attack,
            attack_bonus,
            lethality,
            lethality_bonus,
        )
        outgoing = base_damage * (1.0 + damage_up + attack_damage_up)
        return outgoing * max(0.0, 1.0 - damage_taken_down)

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
