"""Troop base stats and skill rules for WOS battle calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

TROOP_TYPES = ("infantry", "lancer", "marksman")


@dataclass(frozen=True)
class TroopBaseStats:
    troop_type: str
    tier: int
    family_name: str
    fc_level: int
    attack: float
    defense: float
    health: float
    lethality: float


def _rows(troop_type: str, tier: int, values: list[tuple[int, int, int, int]]) -> list[TroopBaseStats]:
    family = "Apex" if tier == 10 else "Helios"
    return [
        TroopBaseStats(troop_type, tier, family, fc + 1, atk, defense, hp, leth)
        for fc, (atk, defense, hp, leth) in enumerate(values)
    ]


TROOP_STATS: Dict[str, TroopBaseStats] = {
    f"{row.troop_type}:t{row.tier}:fc{row.fc_level}": row
    for row in (
        _rows("infantry", 10, [(11,14,16,10),(12,16,17,11),(13,17,18,12),(13,18,19,13),(14,20,20,13),(14,21,21,13),(15,22,22,14),(15,23,23,15),(16,25,24,15),(18,26,25,16)])
        + _rows("infantry", 11, [(13,16,18,12),(14,17,19,13),(15,18,20,14),(15,19,21,15),(16,22,22,15),(17,23,23,16),(17,24,24,16),(18,25,25,17),(18,27,26,17),(19,28,27,18)])
        + _rows("lancer", 10, [(14,12,11,15),(16,13,12,16),(17,14,13,17),(18,14,13,18),(20,15,14,19),(21,15,14,20),(22,16,15,21),(23,17,15,22),(25,17,16,23),(26,19,17,24)])
        + _rows("lancer", 11, [(16,14,13,17),(18,15,14,18),(19,16,15,19),(20,16,15,20),(22,17,16,21),(23,18,16,22),(24,18,17,23),(25,19,17,24),(27,19,18,25),(28,21,20,26)])
        + _rows("marksman", 10, [(15,11,11,16),(17,12,12,17),(18,13,13,18),(19,14,13,19),(21,14,14,20),(22,15,14,21),(23,15,15,22),(24,16,15,23),(26,17,16,24),(27,19,17,25)])
        + _rows("marksman", 11, [(17,13,13,18),(19,14,14,19),(20,15,15,20),(21,16,15,21),(23,16,16,22),(24,17,16,23),(25,18,17,24),(26,19,18,25),(28,19,18,26),(30,21,20,27)])
    )
}


TROOP_SKILL_RULES: List[dict] = [
    {"troopType":"infantry","unlockLevel":1,"skillName":"Master Brawler","effectType":"damage_up_vs_lancer","triggerChance":1.0,"targetType":"lancer","multiplier":0.10,"flatValue":None,"description":"+10% attack damage against Lancers.","enabled":True},
    {"troopType":"infantry","unlockLevel":7,"skillName":"Bands of Steel","effectType":"defense_up_vs_lancer","triggerChance":1.0,"targetType":"lancer","multiplier":0.10,"flatValue":None,"description":"+10% defense against Lancers.","enabled":True},
    {"troopType":"infantry","unlockFcLevel":3,"skillName":"Crystal Shield I","effectType":"damage_offset","triggerChance":0.25,"targetType":"self","multiplier":None,"flatValue":36,"description":"25% chance to offset 36 damage.","enabled":True},
    {"troopType":"infantry","unlockFcLevel":5,"skillName":"Crystal Shield II","effectType":"damage_offset","triggerChance":0.375,"targetType":"self","multiplier":None,"flatValue":36,"description":"37.5% chance to offset 36 damage.","enabled":True},
    {"troopType":"infantry","unlockFcLevel":8,"skillName":"Body of Light I","effectType":"defense_up_and_shield_mitigation","triggerChance":1.0,"targetType":"infantry","multiplier":0.04,"flatValue":None,"description":"+4% Infantry Defense; when Crystal Shield is active, reduce extra 10% damage.","enabled":True},
    {"troopType":"infantry","unlockFcLevel":10,"skillName":"Body of Light II","effectType":"defense_up_and_shield_mitigation","triggerChance":1.0,"targetType":"infantry","multiplier":0.06,"flatValue":None,"description":"+6% Infantry Defense; when Crystal Shield is active, reduce extra 15% damage.","enabled":True},
    {"troopType":"lancer","unlockLevel":1,"skillName":"Charge","effectType":"damage_up_vs_marksman","triggerChance":1.0,"targetType":"marksman","multiplier":0.10,"flatValue":None,"description":"+10% attack damage against Marksmen.","enabled":True},
    {"troopType":"lancer","unlockLevel":7,"skillName":"Ambusher","effectType":"backline_target_chance","triggerChance":0.20,"targetType":"marksman","multiplier":None,"flatValue":None,"description":"20% chance to target Marksmen behind Infantry.","enabled":True},
    {"troopType":"lancer","unlockFcLevel":3,"skillName":"Crystal Lance I","effectType":"double_damage_chance","triggerChance":0.10,"targetType":"current_target","multiplier":2.0,"flatValue":None,"description":"10% chance to deal double damage.","enabled":True},
    {"troopType":"lancer","unlockFcLevel":5,"skillName":"Crystal Lance II","effectType":"double_damage_chance","triggerChance":0.15,"targetType":"current_target","multiplier":2.0,"flatValue":None,"description":"15% chance to deal double damage.","enabled":True},
    {"troopType":"lancer","unlockFcLevel":8,"skillName":"Incandescent Field I","effectType":"half_damage_taken_chance","triggerChance":0.10,"targetType":"self","multiplier":0.5,"flatValue":None,"description":"10% chance to take half damage when attacked.","enabled":True},
    {"troopType":"lancer","unlockFcLevel":10,"skillName":"Incandescent Field II","effectType":"half_damage_taken_chance","triggerChance":0.15,"targetType":"self","multiplier":0.5,"flatValue":None,"description":"15% chance to take half damage when attacked.","enabled":True},
    {"troopType":"marksman","unlockLevel":1,"skillName":"Ranged Strike","effectType":"damage_up_vs_infantry","triggerChance":1.0,"targetType":"infantry","multiplier":0.10,"flatValue":None,"description":"+10% attack damage against Infantry.","enabled":True},
    {"troopType":"marksman","unlockLevel":7,"skillName":"Volley","effectType":"strike_twice_chance","triggerChance":0.10,"targetType":"current_target","multiplier":2.0,"flatValue":None,"description":"10% chance to strike twice.","enabled":True},
    {"troopType":"marksman","unlockFcLevel":3,"skillName":"Crystal Gunpowder I","effectType":"bonus_damage_chance","triggerChance":0.20,"targetType":"current_target","multiplier":1.5,"flatValue":None,"description":"20% chance to deal 50% more damage.","enabled":True},
    {"troopType":"marksman","unlockFcLevel":5,"skillName":"Crystal Gunpowder II","effectType":"bonus_damage_chance","triggerChance":0.30,"targetType":"current_target","multiplier":1.5,"flatValue":None,"description":"30% chance to deal 50% more damage.","enabled":True},
    {"troopType":"marksman","unlockFcLevel":8,"skillName":"Flame Charge I","effectType":"basic_attack_up_and_proc_bonus","triggerChance":1.0,"targetType":"marksman","multiplier":0.04,"flatValue":None,"description":"+4% Marksman basic attack; when Crystal Gunpowder activates, deal extra 25% damage.","enabled":True},
    {"troopType":"marksman","unlockFcLevel":10,"skillName":"Flame Charge II","effectType":"basic_attack_up_and_proc_bonus","triggerChance":1.0,"targetType":"marksman","multiplier":0.06,"flatValue":None,"description":"+6% Marksman basic attack; when Crystal Gunpowder activates, deal extra 37.5% damage.","enabled":True},
]


def get_troop_base_stats(troop_type: str, tier: int, fc_level: int) -> TroopBaseStats:
    key = f"{troop_type}:t{int(tier)}:fc{int(fc_level)}"
    if key not in TROOP_STATS:
        raise ValueError(f"Unknown troop stats for {troop_type} T{tier} FC{fc_level}.")
    return TROOP_STATS[key]


def troop_stats_to_dict(row: TroopBaseStats) -> dict:
    return {
        "troopType": row.troop_type,
        "tier": row.tier,
        "familyName": row.family_name,
        "fcLevel": row.fc_level,
        "attack": row.attack,
        "defense": row.defense,
        "health": row.health,
        "lethality": row.lethality,
    }


def unlocked_troop_skills(troop_type: str, fc_level: int) -> list[dict]:
    return [
        rule for rule in TROOP_SKILL_RULES
        if rule["enabled"]
        and rule["troopType"] == troop_type
        and int(rule.get("unlockFcLevel") or 1) <= int(fc_level)
    ]


def expected_skill_modifiers(troop_type: str, fc_level: int) -> dict:
    damage_up = 0.0
    defense_up = 0.0
    damage_taken_down = 0.0
    notes = []
    for rule in unlocked_troop_skills(troop_type, fc_level):
        chance = float(rule.get("triggerChance") or 0)
        multiplier = rule.get("multiplier")
        effect = rule["effectType"]
        if effect in {"double_damage_chance", "strike_twice_chance"} and multiplier:
            damage_up += chance * (float(multiplier) - 1.0)
        elif effect == "bonus_damage_chance" and multiplier:
            damage_up += chance * (float(multiplier) - 1.0)
        elif effect == "basic_attack_up_and_proc_bonus" and multiplier:
            damage_up += float(multiplier)
        elif effect == "defense_up_and_shield_mitigation" and multiplier:
            defense_up += float(multiplier)
            damage_taken_down += 0.10 if int(fc_level) < 10 else 0.15
        elif effect == "half_damage_taken_chance" and multiplier:
            damage_taken_down += chance * (1.0 - float(multiplier))
        notes.append(rule["skillName"])
    return {
        "damage_up": damage_up,
        "defense_up": defense_up,
        "damage_taken_down": min(damage_taken_down, 0.75),
        "skills": notes,
    }


def all_troop_stats() -> list[dict]:
    return [troop_stats_to_dict(row) for row in TROOP_STATS.values()]
