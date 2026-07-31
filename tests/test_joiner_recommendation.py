"""Transparent tests for the level-5 rally joiner recommendation engine."""

import math
import unittest

from core_engine.joiner_recommendation import (
    CombatBuffs,
    CombatStats,
    HeroJoinerEffect,
    JoinerRecommendationService,
    calculate_balanced_score,
    calculate_counter_multiplier,
    calculate_damage_score,
    calculate_defense_score,
    calculate_effective_attack,
    generate_hero_combinations,
    stack_hero_effects,
)


def effect(hero_id, **values):
    defaults = {
        "hero_id": hero_id,
        "hero_name": hero_id,
        "skill_name": f"{hero_id} Primary",
        "skill_level": 5,
        "stack_group": values.pop("stack_group", "fixture"),
    }
    return HeroJoinerEffect(**defaults, **values)


ATTACK = effect("A", attack_bonus=0.25, stack_group="attack")
LETHALITY = effect("B", lethality_bonus=0.25, stack_group="lethality")
DAMAGE = effect("C", damage_dealt_bonus=0.15, stack_group="damage")
ATTACK_SMALL = effect("D", attack_bonus=0.20, stack_group="attack")
DEFENSE = effect("E", defense_bonus=0.30, stack_group="defense")
HEALTH = effect("F", health_bonus=0.30, stack_group="health")
REDUCTION = effect("G", damage_taken_reduction=0.20, stack_group="reduction")


class FixtureRepository:
    def __init__(self, effects):
        self.effects = effects

    def list_joiner_effects(self):
        return list(self.effects)


class JoinerRecommendationTests(unittest.TestCase):
    def test_01_attack_bonuses_stack_additively(self):
        stacked = stack_hero_effects([ATTACK, ATTACK_SMALL], "infantry")
        self.assertAlmostEqual(stacked.totals["attack_bonus"], 0.45)

    def test_02_lethality_bonuses_stack_additively(self):
        stacked = stack_hero_effects([LETHALITY, LETHALITY], "infantry")
        self.assertAlmostEqual(stacked.totals["lethality_bonus"], 0.50)

    def test_03_damage_dealt_stays_separate_from_attack(self):
        stacked = stack_hero_effects([DAMAGE], "infantry")
        self.assertEqual(stacked.totals["attack_bonus"], 0)
        self.assertAlmostEqual(stacked.totals["damage_dealt_bonus"], 0.15)
        score = calculate_damage_score(CombatStats(), CombatBuffs(), stacked.totals)
        self.assertAlmostEqual(score["score"], 115.0)

    def test_04_damage_reduction_stays_separate_from_defense_and_health(self):
        stacked = stack_hero_effects([REDUCTION], "infantry")
        self.assertEqual(stacked.totals["defense_bonus"], 0)
        self.assertEqual(stacked.totals["health_bonus"], 0)
        score = calculate_defense_score(CombatStats(), CombatBuffs(), stacked.totals)
        self.assertAlmostEqual(score["score"], 125.0)

    def test_05_counter_advantage_is_ten_percent(self):
        self.assertEqual(calculate_counter_multiplier("infantry", "lancer"), 1.10)

    def test_06_no_counter_is_neutral(self):
        self.assertEqual(calculate_counter_multiplier("infantry", "marksman"), 1.00)

    def test_07_unique_combinations_do_not_repeat_heroes(self):
        combos = generate_hero_combinations([ATTACK, LETHALITY, DAMAGE, DEFENSE], 4, False)
        self.assertEqual(len(combos), 1)
        self.assertEqual(len({item.hero_id for item in combos[0]}), 4)

    def test_08_duplicates_are_allowed_when_enabled(self):
        combos = generate_hero_combinations([ATTACK], 4, True)
        self.assertEqual(len(combos), 1)
        self.assertEqual([item.hero_id for item in combos[0]], ["A"] * 4)

    def test_09_maximum_stack_limit_is_respected(self):
        capped = effect("cap", attack_bonus=0.10, stack_group="cap", max_stacks=2)
        self.assertEqual(generate_hero_combinations([capped], 3, True), [])

    def test_10_highest_only_does_not_add_lower_effect(self):
        high = effect("high", attack_bonus=0.40, stack_group="highest", stacking_method="HIGHEST_ONLY")
        low = effect("low", attack_bonus=0.20, stack_group="highest", stacking_method="HIGHEST_ONLY")
        stacked = stack_hero_effects([low, high], "infantry")
        self.assertAlmostEqual(stacked.totals["attack_bonus"], 0.40)

    def test_11_conditional_effect_without_probability_is_excluded(self):
        conditional = effect(
            "conditional",
            attack_bonus=0.50,
            stacking_method="CONDITIONAL",
            activation_condition="after three attacks",
        )
        stacked = stack_hero_effects([conditional], "infantry", "EXPECTED_VALUE")
        self.assertEqual(stacked.totals["attack_bonus"], 0)
        self.assertTrue(stacked.warnings)

    def test_12_max_damage_selects_attack_and_lethality_product(self):
        service = JoinerRecommendationService(repository=FixtureRepository([ATTACK, LETHALITY, DAMAGE]))
        result = service.recommend("MAX_DAMAGE", joiner_count=2, allow_duplicate_heroes=False)
        self.assertEqual({item["heroId"] for item in result["recommendedJoiners"]}, {"A", "B"})
        # (100 * 1.25 * 100 * 1.25) / 100 = 156.25.
        self.assertAlmostEqual(result["scores"]["damageScoreAfterJoiners"], 156.25)

    def test_13_max_defense_selects_defense_and_health_product(self):
        service = JoinerRecommendationService(repository=FixtureRepository([DEFENSE, HEALTH, REDUCTION]))
        result = service.recommend("MAX_DEFENSE", joiner_count=2, allow_duplicate_heroes=False)
        self.assertEqual({item["heroId"] for item in result["recommendedJoiners"]}, {"E", "F"})
        # (100 * 1.30 * 100 * 1.30) / 100 = 169.
        self.assertAlmostEqual(result["scores"]["defenseScoreAfterJoiners"], 169.0)

    def test_14_balanced_score_uses_normalized_geometric_mean(self):
        self.assertAlmostEqual(calculate_balanced_score(1.44, 1.21), math.sqrt(1.44 * 1.21))
        self.assertAlmostEqual(calculate_balanced_score(2.0, 1.0, 0.75, 0.25), 2.0 ** 0.75)

    def test_15_combination_order_does_not_duplicate_results(self):
        combos = generate_hero_combinations([ATTACK, LETHALITY, DAMAGE], 2, False)
        keys = [tuple(sorted(item.hero_id for item in combo)) for combo in combos]
        self.assertEqual(len(keys), len(set(keys)))

    def test_16_tie_breaking_is_deterministic(self):
        one = effect("alpha", attack_bonus=0.10, stack_group="attack")
        two = effect("beta", attack_bonus=0.10, stack_group="attack")
        service = JoinerRecommendationService(repository=FixtureRepository([two, one]))
        winners = [service.recommend("MAX_DAMAGE", 1, False)["recommendedJoiners"][0]["heroId"] for _ in range(3)]
        self.assertEqual(winners, ["alpha", "alpha", "alpha"])

    def test_17_percentages_are_decimal_inputs(self):
        self.assertAlmostEqual(calculate_effective_attack(100, 0.40), 140.0)

    def test_18_calculation_does_not_round_early(self):
        exact = calculate_effective_attack(123.456789, 0.123456789)
        self.assertEqual(exact, 123.456789 * 1.123456789)

    def test_19_enemy_defense_reduction_changes_enemy_defense_side(self):
        reduction = effect("shred", enemy_defense_reduction=0.20, stack_group="enemy-defense")
        totals = stack_hero_effects([reduction], "marksman").totals
        before = calculate_damage_score(
            CombatStats(), CombatBuffs(), troop_type="marksman", enemy_stats=CombatStats(defense=200, health=100)
        )
        after = calculate_damage_score(
            CombatStats(), CombatBuffs(), totals, "marksman", None, CombatStats(defense=200, health=100)
        )
        self.assertGreater(after["score"], before["score"])
        self.assertAlmostEqual(after["penetration_score"], 100 / 260 * 100 / 200)

    def test_20_inventory_counts_limit_duplicate_recommendations(self):
        combos = generate_hero_combinations(
            [ATTACK, LETHALITY],
            4,
            True,
            available_counts={"A": 1, "B": 3},
        )
        self.assertEqual(len(combos), 1)
        self.assertEqual(CounterIds(combos[0]), {"A": 1, "B": 3})

    def test_21_multiplicative_effects_are_not_added(self):
        first = effect("m1", damage_dealt_bonus=0.10, stack_group="multi", stacking_method="MULTIPLICATIVE")
        second = effect("m2", damage_dealt_bonus=0.20, stack_group="multi", stacking_method="MULTIPLICATIVE")
        stacked = stack_hero_effects([first, second], "infantry")
        self.assertAlmostEqual(stacked.totals["damage_dealt_bonus"], 0.32)

    def test_22_expected_value_uses_supplied_probability(self):
        conditional = effect(
            "conditional",
            attack_bonus=0.50,
            stacking_method="CONDITIONAL",
            activation_condition="sometimes",
        )
        stacked = stack_hero_effects(
            [conditional], "infantry", "EXPECTED_VALUE", {"conditional": 0.40}
        )
        self.assertAlmostEqual(stacked.totals["attack_bonus"], 0.20)

    def test_23_damage_reduction_at_one_hundred_percent_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot reach or exceed 100%"):
            calculate_defense_score(
                CombatStats(), CombatBuffs(), {"damage_taken_reduction": 1.0}
            )


def CounterIds(combination):
    counts = {}
    for item in combination:
        counts[item.hero_id] = counts.get(item.hero_id, 0) + 1
    return counts


if __name__ == "__main__":
    unittest.main()
