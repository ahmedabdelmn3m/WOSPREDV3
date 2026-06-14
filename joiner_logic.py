"""
Logic for applying hero joiner bonuses to a rally leader's base stats.
"""

from typing import List
from hero_data import HEROES

def apply_joiner_bonuses(base_attack_bonus: float, base_lethality_bonus: float, joiners_list: List[str]) -> tuple[float, float]:
    """
    Calculates the new total attack and lethality bonuses after adding joiner expedition skills.
    
    Parameters
    ----------
    base_attack_bonus    : The rally leader's existing attack bonus (decimal).
    base_lethality_bonus : The rally leader's existing lethality bonus (decimal).
    joiners_list         : List of up to 4 hero names.
    
    Returns
    -------
    (new_attack_bonus, new_lethality_bonus) in decimal form.
    """
    total_atk_gain = 0.0
    total_lth_gain = 0.0
    
    # Process only up to the first 4 joiners
    for name in joiners_list[:4]:
        hero = HEROES.get(name)
        if not hero:
            continue
            
        if hero.skill_type == "attack_only":
            total_atk_gain += hero.bonus_pct
        elif hero.skill_type == "attack_and_lethality":
            total_atk_gain += hero.bonus_pct
            total_lth_gain += hero.bonus_pct
            
    return (base_attack_bonus + total_atk_gain, base_lethality_bonus + total_lth_gain)
