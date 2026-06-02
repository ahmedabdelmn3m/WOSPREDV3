import unittest
from core_engine.damage_model import DamageModel

class TestDamageModel(unittest.TestCase):
    def test_calculation(self):
        # Damage = 100 / (Attack * (1 + ΣAttackStats) * Lethality * (1 + ΣLethalityStats))
        res = DamageModel.calculate_damage(10, 0.5, 5, 0.2)
        # 100 / (10 * 1.5 * 5 * 1.2) = 100 / (15 * 6) = 100 / 90 = 1.11...
        self.assertAlmostEqual(res, 1.11111111)

if __name__ == '__main__':
    unittest.main()
