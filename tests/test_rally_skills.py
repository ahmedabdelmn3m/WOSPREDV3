from hero_data import HEROES_BY_ID
from joiner_logic import (
    apply_garrison_primary_skills,
    apply_joiner_primary_skills,
    apply_leader_skills,
    calculate_rally_effective_modifiers,
    validate_main_march,
)


def test_only_first_4_joiners_are_applied():
    result = apply_joiner_primary_skills(["jessie", "jasser", "seo-yoon", "philly", "reina"])
    assert result["applied_count"] == 4
    assert result["modifiers"]["infantry"]["attack_damage_up"] == 0


def test_only_primary_skill_slot_is_applied_for_joiners():
    hero = HEROES_BY_ID["jessie"]
    assert hero.primary_skill().slot == 1
    result = apply_joiner_primary_skills(["jessie"])
    assert result["applied_count"] == 1
    assert result["modifiers"]["infantry"]["damage_up"] == 0.25


def test_seo_yoon_corrected_to_damage_up_all_troops():
    skill = HEROES_BY_ID["seo-yoon"].primary_skill()
    assert skill.effect_type == "damage_up"
    assert skill.value_pct == 25.0
    assert skill.target_scope == "all_troops"
    result = apply_joiner_primary_skills(["seo-yoon"])
    assert result["modifiers"]["infantry"]["damage_up"] == 0.25
    assert result["modifiers"]["lancer"]["damage_up"] == 0.25
    assert result["modifiers"]["marksman"]["damage_up"] == 0.25
    assert result["modifiers"]["infantry"]["attack_up"] == 0


def test_flint_damage_up_is_infantry_only():
    result = apply_joiner_primary_skills(["flint"])
    assert result["modifiers"]["infantry"]["damage_up"] == 1.0
    assert result["modifiers"]["lancer"]["damage_up"] == 0
    assert result["modifiers"]["marksman"]["damage_up"] == 0


def test_jessie_jasser_seo_yoon_damage_up_applies_to_all_troops():
    result = apply_joiner_primary_skills(["jessie", "jasser", "seo-yoon"])
    for troop in ("infantry", "lancer", "marksman"):
        assert result["modifiers"][troop]["damage_up"] == 0.75


def test_philly_attack_up_is_separate_from_damage_up():
    result = apply_joiner_primary_skills(["philly"])
    for troop in ("infantry", "lancer", "marksman"):
        assert result["modifiers"][troop]["attack_up"] == 0.15
        assert result["modifiers"][troop]["damage_up"] == 0


def test_leader_applies_all_skills_from_three_heroes():
    result = apply_leader_skills(["jeronimo", "flint", "reina"])
    assert result["applied_count"] == 3
    assert result["modifiers"]["infantry"]["damage_up"] == 1.25
    assert result["modifiers"]["lancer"]["attack_damage_up"] == 0.30
    assert result["modifiers"]["marksman"]["attack_damage_up"] == 0.30


def test_garrison_uses_same_primary_skill_limit_as_joiners():
    result = apply_garrison_primary_skills(["jessie", "jasser", "seo-yoon", "philly", "reina"])
    assert result["applied_count"] == 4
    assert result["modifiers"]["infantry"]["attack_damage_up"] == 0


def test_main_march_validation_valid_and_invalid_cases():
    assert validate_main_march(["hector", "norah", "gwen"]) == []
    assert "Duplicate hero type selected." in validate_main_march(["hector", "flint", "gwen"])
    assert "Duplicate hero ID selected." in validate_main_march(["hector", "hector", "gwen"])
    assert "Main march must include exactly 1 Infantry, 1 Lancer, and 1 Marksman hero." in validate_main_march(["hector", "gwen"])


def test_combined_rally_modifiers_respect_target_scope():
    result = calculate_rally_effective_modifiers(
        leader_march=["hector", "norah", "gwen"],
        joiner_heroes=["flint", "philly"],
        widgets=[],
    )
    assert result["modifiers"]["infantry"]["damage_up"] == 1.0
    assert result["modifiers"]["lancer"]["damage_up"] == 0
    assert result["modifiers"]["marksman"]["damage_up"] == 0
    assert result["modifiers"]["marksman"]["attack_up"] == 0.15


def test_widget_level_zero_blocks_where_required():
    selected = {"hero_id": "jeronimo", "widget_level": 0, "widget_required": True}
    errors = []
    if selected["widget_required"] and selected["widget_level"] <= 0:
        errors.append("Widget level cannot be 0.")
    assert errors == ["Widget level cannot be 0."]
