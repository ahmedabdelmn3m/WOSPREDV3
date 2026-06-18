"""
Tests for Tier 1 (formula fixes) + Tier 2 (troop-type architecture).

Run with:  python -m unittest discover tests
"""

import unittest

from core_engine.damage_model  import DamageModel
from core_engine.defense_model import DefenseModel
from core_engine.troop_stats   import TroopTypeStats, Formation, ArmyStats
from core_engine.turn_resolver  import TurnResolver
from core_engine.battle_simulator import BattleSimulator
from core_engine.combat_engine  import CombatEngine


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Tier 1 â€” Formula correctness
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestDamageFormula(unittest.TestCase):
    """
    Verified formula:
        damage = (attack Ã— (1 + attack_bonus) Ã— lethality Ã— (1 + lethality_bonus)) / 100
    """

    def test_basic(self):
        # (1 Ã— 2.50 Ã— 1 Ã— 1.80) / 100 = 4.50 / 100 = 0.045
        result = DamageModel.calculate(1.0, 1.50, 1.0, 0.80)
        self.assertAlmostEqual(result, 0.045, places=8)

    def test_zero_bonuses(self):
        # (1 Ã— 1 Ã— 1 Ã— 1) / 100 = 0.01
        result = DamageModel.calculate(1.0, 0.0, 1.0, 0.0)
        self.assertAlmostEqual(result, 0.01, places=8)

    def test_high_bonuses(self):
        # (1 Ã— 3.0 Ã— 1 Ã— 2.0) / 100 = 0.06
        result = DamageModel.calculate(1.0, 2.0, 1.0, 1.0)
        self.assertAlmostEqual(result, 0.06, places=8)

    def test_is_not_inverted(self):
        """Confirm we are NOT using the old wrong formula (100 / ...)."""
        result = DamageModel.calculate(1.0, 1.0, 1.0, 1.0)
        # Correct:  (1 Ã— 2 Ã— 1 Ã— 2) / 100  = 0.04
        # Wrong:    100 / (1 Ã— 2 Ã— 1 Ã— 2)  = 25.0
        self.assertAlmostEqual(result, 0.04, places=8)
        self.assertNotAlmostEqual(result, 25.0, places=1)

    def test_legacy_alias(self):
        r1 = DamageModel.calculate(1.0, 0.5, 1.0, 0.3)
        r2 = DamageModel.calculate_damage(1.0, 0.5, 1.0, 0.3)
        self.assertEqual(r1, r2)


class TestDefenseFormula(unittest.TestCase):
    """
    Verified formula:
        defense = (defense Ã— (1 + defense_bonus) Ã— health Ã— (1 + health_bonus)) / 100
    """

    def test_basic(self):
        # (1 Ã— 2.20 Ã— 1 Ã— 3.00) / 100 = 6.60 / 100 = 0.066
        result = DefenseModel.calculate(1.0, 1.20, 1.0, 2.00)
        self.assertAlmostEqual(result, 0.066, places=8)

    def test_zero_bonuses(self):
        # (1 Ã— 1 Ã— 1 Ã— 1) / 100 = 0.01
        result = DefenseModel.calculate(1.0, 0.0, 1.0, 0.0)
        self.assertAlmostEqual(result, 0.01, places=8)

    def test_is_not_inverted(self):
        """Confirm we are NOT using the old wrong formula (100 Ã— ...)."""
        result = DefenseModel.calculate(1.0, 1.0, 1.0, 1.0)
        # Correct:  (1 Ã— 2 Ã— 1 Ã— 2) / 100  = 0.04
        # Wrong:    100 Ã— 1 Ã— 2 Ã— 1 Ã— 2     = 400.0
        self.assertAlmostEqual(result, 0.04, places=8)
        self.assertNotAlmostEqual(result, 400.0, places=1)

    def test_legacy_alias(self):
        r1 = DefenseModel.calculate(1.0, 0.5, 1.0, 0.3)
        r2 = DefenseModel.calculate_defense_power(1.0, 0.5, 1.0, 0.3)
        self.assertEqual(r1, r2)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Tier 2 â€” Troop-type architecture
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestTroopTypeStats(unittest.TestCase):

    def test_effective_damage_from_percentages(self):
        troop = TroopTypeStats.from_percentages(
            attack_pct=150.0, lethality_pct=80.0,
            defense_pct=120.0, health_pct=200.0,
        )
        # attack_bonus=1.50, lethality_bonus=0.80
        # (1 Ã— 2.50 Ã— 1 Ã— 1.80) / 100 = 0.045
        self.assertAlmostEqual(troop.effective_damage, 0.045, places=8)

    def test_effective_defense_from_percentages(self):
        troop = TroopTypeStats.from_percentages(
            attack_pct=150.0, lethality_pct=80.0,
            defense_pct=120.0, health_pct=200.0,
        )
        # defense_bonus=1.20, health_bonus=2.00
        # (1 Ã— 2.20 Ã— 1 Ã— 3.00) / 100 = 0.066
        self.assertAlmostEqual(troop.effective_defense, 0.066, places=8)

    def test_to_dict_has_computed_fields(self):
        troop = TroopTypeStats.from_percentages(150.0, 120.0, 200.0, 80.0)
        d = troop.to_dict()
        self.assertIn("effective_damage",  d)
        self.assertIn("effective_defense", d)


class TestFormation(unittest.TestCase):

    def test_valid_formation(self):
        f = Formation(0.50, 0.20, 0.30)
        f.validate()  # Should not raise

    def test_invalid_formation_raises(self):
        f = Formation(0.50, 0.30, 0.30)  # sums to 1.10
        with self.assertRaises(ValueError):
            f.validate()

    def test_from_percentages(self):
        f = Formation.from_percentages(50.0, 20.0, 30.0)
        self.assertAlmostEqual(f.infantry, 0.50, places=4)
        self.assertAlmostEqual(f.lancer,   0.20, places=4)
        self.assertAlmostEqual(f.marksman, 0.30, places=4)


class TestArmyStats(unittest.TestCase):

    def _make_army(self, troop_count: int = 100_000) -> ArmyStats:
        """Helper â€” returns a standard test army."""
        return ArmyStats.from_scout(
            name="TestArmy",
            infantry={"attack_pct": 150, "defense_pct": 120,
                      "health_pct": 200, "lethality_pct": 80},
            lancer={"attack_pct": 100, "defense_pct": 100,
                    "health_pct": 150, "lethality_pct": 60},
            marksman={"attack_pct": 200, "defense_pct": 100,
                      "health_pct": 150, "lethality_pct": 100},
            formation={"infantry": 0.50, "lancer": 0.20, "marksman": 0.30},
            troop_count=troop_count,
        )

    def test_army_damage_is_weighted_sum(self):
        army = self._make_army()
        expected = (
            0.50 * army.infantry.effective_damage  +
            0.20 * army.lancer.effective_damage    +
            0.30 * army.marksman.effective_damage
        )
        self.assertAlmostEqual(army.army_damage(), expected, places=8)

    def test_army_defense_is_weighted_sum(self):
        army = self._make_army()
        expected = (
            0.50 * army.infantry.effective_defense  +
            0.20 * army.lancer.effective_defense    +
            0.30 * army.marksman.effective_defense
        )
        self.assertAlmostEqual(army.army_defense(), expected, places=8)

    def test_troop_breakdown_sums_to_total(self):
        army = self._make_army(500_000)
        bd = army.troop_breakdown()
        self.assertAlmostEqual(
            bd["infantry"] + bd["lancer"] + bd["marksman"],
            500_000,
            delta=3,  # small rounding tolerance from int()
        )

    def test_from_scout_parses_correctly(self):
        army = self._make_army()
        self.assertEqual(army.name, "TestArmy")
        self.assertAlmostEqual(army.infantry.attack_bonus, 1.50, places=4)
        self.assertAlmostEqual(army.marksman.lethality_bonus, 1.00, places=4)

    def test_stat_summary_keys(self):
        keys = self._make_army().stat_summary().keys()
        for k in ("name", "troop_count", "formation", "army_damage", "army_defense",
                  "infantry", "lancer", "marksman"):
            self.assertIn(k, keys)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Integration â€” full battle simulation
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBattleSimulation(unittest.TestCase):

    def _make_army(self, attack_pct: float, defense_pct: float,
                   health_pct: float, lethality_pct: float,
                   troop_count: int = 100_000,
                   name: str = "Army") -> ArmyStats:
        """All troop types have the same stats for predictable testing."""
        stats = {
            "attack_pct": attack_pct,
            "defense_pct": defense_pct,
            "health_pct": health_pct,
            "lethality_pct": lethality_pct,
        }
        return ArmyStats.from_scout(
            name=name,
            infantry=stats, lancer=stats, marksman=stats,
            formation={"infantry": 0.50, "lancer": 0.20, "marksman": 0.30},
            troop_count=troop_count,
        )

    def test_stronger_attacker_wins(self):
        """An army with much higher attack and lethality should beat a weaker defender."""
        strong = self._make_army(300, 200, 300, 200, name="Strong")
        weak   = self._make_army(50,   50,  50,  50, name="Weak")
        engine = CombatEngine()
        result = engine.run_battle(strong, weak)
        self.assertEqual(result["winner"], "attacker")

    def test_loser_has_zero_survivors(self):
        """The result summary should show no surviving troops on the losing side."""
        strong = self._make_army(300, 200, 300, 200, name="Strong")
        weak   = self._make_army(50,   50,  50,  50, name="Weak")
        result = CombatEngine().run_battle(strong, weak)

        self.assertEqual(result["winner"], "attacker")
        self.assertEqual(result["defender"]["survivors"], 0)
        self.assertEqual(result["defender"]["casualties"], result["defender"]["initial_troops"])
        self.assertEqual(result["defender"]["loss_rate"], 1.0)

    def test_result_has_required_keys(self):
        army = self._make_army(150, 120, 200, 80)
        result = CombatEngine().run_battle(army, army)
        for key in ("winner", "rounds_played", "attacker", "defender", "history"):
            self.assertIn(key, result)

    def test_attacker_result_has_survivor_info(self):
        army = self._make_army(150, 120, 200, 80)
        result = CombatEngine().run_battle(army, army)
        for side in ("attacker", "defender"):
            for field in ("initial_troops", "survivors", "casualties", "loss_rate"):
                self.assertIn(field, result[side])

    def test_original_army_not_mutated(self):
        """simulate() must not modify the input ArmyStats objects."""
        army = self._make_army(150, 120, 200, 80, troop_count=500_000)
        _ = CombatEngine().run_battle(army, army)
        self.assertEqual(army.troop_count, 500_000)

    def test_rounds_within_max(self):
        army = self._make_army(100, 100, 100, 100)
        result = CombatEngine().run_battle(army, army, max_rounds=10)
        self.assertLessEqual(result["rounds_played"], 10)

    def test_history_contains_round_dicts(self):
        army = self._make_army(150, 120, 200, 80)
        result = CombatEngine().run_battle(army, army)
        self.assertGreater(len(result["history"]), 0)
        first = result["history"][0]
        self.assertIn("round",    first)
        self.assertIn("attacker", first)
        self.assertIn("defender", first)


if __name__ == "__main__":
    unittest.main()
