from troop_data import get_troop_base_stats
from api.main import TroopStatsInput


def test_t10_infantry_fc1_stats():
    stats = get_troop_base_stats("infantry", 10, 1)
    assert stats.attack == 11
    assert stats.defense == 14
    assert stats.health == 16
    assert stats.lethality == 10


def test_t11_infantry_fc10_stats():
    stats = get_troop_base_stats("infantry", 11, 10)
    assert stats.attack == 19
    assert stats.defense == 28
    assert stats.health == 27
    assert stats.lethality == 18


def test_t11_marksman_fc10_stats():
    stats = get_troop_base_stats("marksman", 11, 10)
    assert stats.attack == 30
    assert stats.defense == 21
    assert stats.health == 20
    assert stats.lethality == 27


def test_effective_stat_calculation_applies_scout_percentages():
    stats = TroopStatsInput(
        troop_type="infantry",
        tier=10,
        fc_level=1,
        attack_pct=100,
        defense_pct=50,
        health_pct=25,
        lethality_pct=10,
    ).to_troop_type_stats("infantry")
    assert stats.attack == 11
    assert stats.attack_bonus == 1.0
    assert stats.defense == 14
    assert stats.defense_bonus == 0.5
    assert stats.health == 16
    assert stats.health_bonus == 0.25
    assert stats.lethality == 10
    assert stats.lethality_bonus == 0.10
