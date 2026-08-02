"""Evidence-backed stacking, target-goal, and formation-weighting regressions."""

import unittest

from core_engine.joiner_recommendation import (
    CombatBuffs,
    CombatStats,
    HeroJoinerRepository,
    JoinerRecommendationService,
    calculate_damage_score,
    calculate_defense_score,
    stack_hero_effects,
)
from hero_data import HEROES_BY_ID


class JoinerStackPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = {
            effect.hero_id: effect
            for effect in HeroJoinerRepository().list_joiner_effects()
        }

    def test_required_level_five_first_skills_are_configured(self):
        expected = {
            "jessie": ("damage_up", 25.0),
            "jasser": ("damage_up", 25.0),
            "seo-yoon": ("attack_up", 25.0),
            "lumak": ("enemy_damage_dealt_down", 20.0),
            "ling": ("enemy_attack_down", 20.0),
            "patrick": ("health_up", 25.0),
            "sergey": ("damage_taken_down", 20.0),
            "gwen": ("enemy_damage_taken_up", 25.0),
            "philly": ("attack_up", 15.0),
            "flint": ("damage_up", 100.0),
        }
        for hero_id, (effect_type, value) in expected.items():
            primary = HEROES_BY_ID[hero_id].primary_skill()
            self.assertEqual(primary.skill_level, 5)
            self.assertEqual(primary.effect_type, effect_type)
            self.assertEqual(primary.value_pct, value)

    def test_philly_primary_skill_has_attack_and_defense_components(self):
        philly = self.effects["philly"]
        self.assertAlmostEqual(philly.attack_bonus, 0.15)
        self.assertAlmostEqual(philly.defense_bonus, 0.10)
        self.assertEqual(
            {component.canonical_key_text for component in philly.components},
            {
                "friendly:all_troops:attack_bonus",
                "friendly:all_troops:defense_bonus",
            },
        )

    def test_equal_damage_keys_add_and_attack_multiplies_in_equation(self):
        stacked = stack_hero_effects(
            [self.effects["jessie"], self.effects["jasser"], self.effects["seo-yoon"]],
            "marksman",
        )
        self.assertAlmostEqual(stacked.totals["damage_dealt_bonus"], 0.50)
        self.assertAlmostEqual(stacked.totals["attack_bonus"], 0.25)
        score = calculate_damage_score(CombatStats(), CombatBuffs(), stacked, "marksman")
        self.assertAlmostEqual(score["score"], 187.5)

    def test_flint_scope_multiplies_with_all_troop_damage_bucket(self):
        infantry = stack_hero_effects(
            [self.effects["jessie"], self.effects["flint"]],
            "infantry",
        )
        marksman = stack_hero_effects(
            [self.effects["jessie"], self.effects["flint"]],
            "marksman",
        )
        self.assertAlmostEqual(infantry.totals["damage_dealt_bonus"], 1.50)
        self.assertAlmostEqual(marksman.totals["damage_dealt_bonus"], 0.25)
        score = calculate_damage_score(
            CombatStats(),
            CombatBuffs(damage_dealt=0.20),
            infantry,
            "infantry",
        )
        self.assertAlmostEqual(score["damage_multiplier"], 2.90)

    def test_four_distinct_defensive_layers_use_reciprocal_model(self):
        stacked = stack_hero_effects(
            [
                self.effects["patrick"],
                self.effects["ling"],
                self.effects["lumak"],
                self.effects["sergey"],
            ],
            "infantry",
        )
        score = calculate_defense_score(CombatStats(), CombatBuffs(), stacked)
        self.assertAlmostEqual(score["score"], 216.0)
        self.assertAlmostEqual(score["incoming_damage_multiplier"], 1 / (1.2 ** 3))

    def test_gwen_is_excluded_by_default_and_modelable_when_enabled(self):
        service = JoinerRecommendationService()
        with self.assertRaisesRegex(ValueError, "No eligible"):
            service.recommend(
                "MAX_DAMAGE",
                joiner_count=1,
                available_hero_ids=["gwen"],
            )
        result = service.recommend(
            "MAX_DAMAGE",
            joiner_count=1,
            available_hero_ids=["gwen"],
            include_experimental_skills=True,
        )
        self.assertEqual(result["recommendedJoiners"][0]["heroId"], "gwen")
        self.assertTrue(result["recommendedJoiners"][0]["experimental"])

    def test_kill_lancers_resolves_to_infantry_counter(self):
        result = JoinerRecommendationService().recommend(
            "KILL_LANCERS",
            joiner_count=1,
            allow_duplicate_heroes=False,
            available_hero_ids=["flint", "jessie"],
        )
        self.assertEqual(result["targetTroopType"], "infantry")
        self.assertEqual(result["enemyTroopType"], "lancer")
        self.assertEqual(result["recommendedJoiners"][0]["heroId"], "flint")

    def test_flint_is_formation_weighted_not_whole_army_plus_one_hundred(self):
        result = JoinerRecommendationService().recommend(
            "KILL_LANCERS",
            joiner_count=1,
            allow_duplicate_heroes=False,
            available_hero_ids=["flint"],
            troop_split={"infantry": 40, "lancer": 30, "marksman": 30},
        )
        scores = result["scores"]
        self.assertAlmostEqual(scores["targetDamageImprovementPercentage"], 100.0)
        self.assertAlmostEqual(scores["damageScoreBeforeJoiners"], 104.0)
        self.assertAlmostEqual(scores["damageScoreAfterJoiners"], 148.0)
        self.assertLess(scores["damageImprovementPercentage"], 50.0)

    def test_garrison_hold_selects_four_distinct_defensive_layers(self):
        result = JoinerRecommendationService().recommend(
            "GARRISON_HOLD",
            joiner_count=4,
            allow_duplicate_heroes=False,
            available_hero_ids=["patrick", "ling", "lumak", "sergey", "philly", "flint"],
        )
        self.assertEqual(
            {entry["heroId"] for entry in result["recommendedJoiners"]},
            {"patrick", "ling", "lumak", "sergey"},
        )
        self.assertAlmostEqual(result["scores"]["defenseScoreAfterJoiners"], 216.0)


if __name__ == "__main__":
    unittest.main()
