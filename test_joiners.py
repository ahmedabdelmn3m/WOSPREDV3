"""
Tests for the Hero Joiner logic.
"""

from joiner_logic import apply_joiner_bonuses
from core_engine.damage_model import DamageModel

def test_jessie_jasser():
    # Base: 100% bonus (1.0)
    base_atk = 1.0
    base_lth = 1.0
    
    # Jessie (25/25) + Jasser (25/25)
    new_atk, new_lth = apply_joiner_bonuses(base_atk, base_lth, ["Jessie", "Jasser"])
    
    # Expected: 1.0 + 0.25 + 0.25 = 1.5
    assert new_atk == 1.5
    assert new_lth == 1.5
    
    # Damage calculation: (1.0 * (1+1.5) * 1.0 * (1+1.5)) / 100 = (2.5 * 2.5) / 100 = 0.0625
    damage = DamageModel.calculate(1.0, new_atk, 1.0, new_lth)
    assert damage == 0.0625
    print("Test Jessie + Jasser: PASSED")

def test_seo_yoon_vs_jessie():
    # Base: 0% bonus (0.0), Base stats: 100
    base_atk_bonus = 0.0
    base_lth_bonus = 0.0
    base_val = 100.0
    
    # Seo-Yoon: 50% atk only
    atk_seo, lth_seo = apply_joiner_bonuses(base_atk_bonus, base_lth_bonus, ["Seo-Yoon"])
    dmg_seo = DamageModel.calculate(base_val, atk_seo, base_val, lth_seo)
    # (100 * 1.5 * 100 * 1.0) / 100 = 150
    
    # Jessie: 25% atk, 25% lth
    atk_jessie, lth_jessie = apply_joiner_bonuses(base_atk_bonus, base_lth_bonus, ["Jessie"])
    dmg_jessie = DamageModel.calculate(base_val, atk_jessie, base_val, lth_jessie)
    # (100 * 1.25 * 100 * 1.25) / 100 = 156.25
    
    assert dmg_jessie > dmg_seo
    print(f"Test Seo-Yoon ({dmg_seo}) vs Jessie ({dmg_jessie}): PASSED (Jessie is better)")

if __name__ == "__main__":
    test_jessie_jasser()
    test_seo_yoon_vs_jessie()
    print("\nAll Joiner Logic Tests: PASSED")
