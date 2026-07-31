"""
Tests for the Hero Joiner logic.
"""

from joiner_logic import apply_joiner_primary_skills
from core_engine.damage_model import DamageModel

def test_jessie_jasser():
    result = apply_joiner_primary_skills(["Jessie", "Jasser"])
    modifiers = result["modifiers"]["infantry"]
    assert modifiers["attack_up"] == 0
    assert modifiers["lethality_up"] == 0
    assert modifiers["damage_up"] == 0.50
    damage = DamageModel.calculate_with_layers(1.0, 1.0, 1.0, 1.0, damage_up=0.50)
    assert damage == 0.06
    print("Test Jessie + Jasser: PASSED")

def test_seo_yoon_vs_jessie():
    seo = apply_joiner_primary_skills(["Seo-Yoon"])["modifiers"]["infantry"]
    jessie = apply_joiner_primary_skills(["Jessie"])["modifiers"]["infantry"]
    assert seo["damage_up"] == 0.25
    assert jessie["damage_up"] == 0.25
    assert seo == jessie

if __name__ == "__main__":
    test_jessie_jasser()
    test_seo_yoon_vs_jessie()
    print("\nAll Joiner Logic Tests: PASSED")
