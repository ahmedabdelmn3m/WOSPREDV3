"""
Rally, joiner, and garrison hero skill mechanics.

Official FAQ interpretation used here:
- Rally leader applies the full 3-hero march skill set.
- Rally joiners apply only the first/primary skill from up to 4 joining heroes.
- Garrison helper heroes use the same primary-skill, max-4 support rule.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from hero_data import EFFECT_TYPES, TROOP_TYPES, ExpeditionSkill, Hero, get_hero


ModifierMap = Dict[str, Dict[str, float]]


def empty_modifiers() -> ModifierMap:
    return {
        troop: {
            "attack_up": 0.0,
            "damage_up": 0.0,
            "attack_damage_up": 0.0,
            "lethality_up": 0.0,
            "defense_up": 0.0,
            "health_up": 0.0,
            "damage_taken_down": 0.0,
        }
        for troop in TROOP_TYPES
    }


def validate_main_march(march_heroes: Iterable[Any]) -> List[str]:
    heroes = [get_hero(item) for item in march_heroes]
    heroes = [hero for hero in heroes if hero]
    errors: List[str] = []

    if len(heroes) != 3:
        errors.append("Main march must include exactly 3 heroes.")

    ids = [hero.id for hero in heroes]
    if len(set(ids)) != len(ids):
        errors.append("Duplicate hero ID selected.")

    types = [hero.hero_type for hero in heroes]
    if len(set(types)) != len(types):
        errors.append("Duplicate hero type selected.")

    required = set(TROOP_TYPES)
    if set(types) != required:
        errors.append("Main march must include exactly 1 Infantry, 1 Lancer, and 1 Marksman hero.")

    return errors


def apply_leader_skills(leader_march: Iterable[Any]) -> dict:
    heroes = [hero for hero in (get_hero(item) for item in leader_march) if hero]
    breakdown = []
    modifiers = empty_modifiers()
    for hero in heroes[:3]:
        for skill in hero.expedition_skills:
            _apply_skill(modifiers, skill)
            breakdown.append(_skill_breakdown(hero, skill, "leader_full"))
    return {"modifiers": modifiers, "breakdown": breakdown, "applied_count": len(breakdown)}


def apply_joiner_primary_skills(joiner_heroes: Iterable[Any]) -> dict:
    return _apply_primary_support_skills(joiner_heroes, "joiner_primary")


def apply_garrison_primary_skills(garrison_joiner_heroes: Iterable[Any]) -> dict:
    return _apply_primary_support_skills(garrison_joiner_heroes, "garrison_primary")


def calculate_rally_effective_modifiers(
    leader_march: Iterable[Any],
    joiner_heroes: Iterable[Any],
    widgets: Optional[Iterable[dict]] = None,
) -> dict:
    leader = apply_leader_skills(leader_march)
    joiners = apply_joiner_primary_skills(joiner_heroes)
    combined = combine_modifiers(leader["modifiers"], joiners["modifiers"])
    widget_breakdown = []

    for widget in widgets or []:
        skill = _widget_to_skill(widget)
        if not skill:
            continue
        _apply_skill(combined, skill)
        widget_breakdown.append({"source": "widget", "skill": skill.__dict__})

    return {
        "modifiers": combined,
        "leader": leader,
        "joiners": joiners,
        "widgets": widget_breakdown,
        "formula_note": (
            "Base damage remains attack/lethality driven; damage_up and "
            "attack_damage_up are applied as final damage multipliers. "
            "damage_taken_down mitigates incoming final damage where modeled."
        ),
    }


def combine_modifiers(*maps: ModifierMap) -> ModifierMap:
    combined = empty_modifiers()
    for modifier_map in maps:
        for troop in TROOP_TYPES:
            for effect in combined[troop]:
                combined[troop][effect] += modifier_map.get(troop, {}).get(effect, 0.0)
    return combined


def apply_joiner_bonuses(
    base_attack_bonus: float,
    base_lethality_bonus: float,
    joiners_list: List[str],
) -> tuple[float, float]:
    """
    Compatibility wrapper for older call-sites.

    It only returns attack/lethality layers. Damage Up and Attack Damage Up are
    intentionally not folded into Attack Up.
    """
    result = apply_joiner_primary_skills(joiners_list)
    all_troop = result["modifiers"]["infantry"]
    return (
        base_attack_bonus + all_troop["attack_up"],
        base_lethality_bonus + all_troop["lethality_up"],
    )


def _apply_primary_support_skills(heroes_like: Iterable[Any], source_label: str) -> dict:
    modifiers = empty_modifiers()
    breakdown = []
    heroes = [hero for hero in (get_hero(item) for item in heroes_like) if hero]
    for hero in heroes[:4]:
        primary = hero.primary_skill()
        if not primary:
            breakdown.append({
                "hero_id": hero.id,
                "hero_name": hero.name,
                "source": source_label,
                "skill": None,
                "notes": "No verified primary expedition skill value is configured.",
            })
            continue
        _apply_skill(modifiers, primary)
        breakdown.append(_skill_breakdown(hero, primary, source_label))
    return {"modifiers": modifiers, "breakdown": breakdown, "applied_count": len(breakdown)}


def _apply_skill(modifiers: ModifierMap, skill: ExpeditionSkill) -> None:
    if skill.effect_type not in EFFECT_TYPES or skill.effect_type == "unknown":
        return
    targets = TROOP_TYPES if skill.target_scope == "all_troops" else (skill.target_scope,)
    for troop in targets:
        if troop in modifiers and skill.effect_type in modifiers[troop]:
            modifiers[troop][skill.effect_type] += skill.value_decimal


def _skill_breakdown(hero: Hero, skill: ExpeditionSkill, source_label: str) -> dict:
    return {
        "hero_id": hero.id,
        "hero_name": hero.name,
        "source": source_label,
        "slot": skill.slot,
        "skill_name": skill.name,
        "effect_type": skill.effect_type,
        "value_pct": skill.value_pct,
        "target_scope": skill.target_scope,
        "data_source": skill.source,
        "confidence": skill.confidence,
        "notes": skill.notes,
    }


def _widget_to_skill(widget: dict) -> Optional[ExpeditionSkill]:
    if not widget or not widget.get("effect_type") or not widget.get("value_pct"):
        return None
    return ExpeditionSkill(
        slot=0,
        name=widget.get("name", "Widget"),
        effect_type=widget["effect_type"],
        value_pct=float(widget["value_pct"]),
        target_scope=widget.get("target_scope") or "all_troops",
        applies_to="both",
        source=widget.get("source", "unknown"),
        confidence=widget.get("confidence", "low"),
        notes=widget.get("notes", "Widget effect supplied externally."),
    )


def clone_modifiers(modifiers: ModifierMap) -> ModifierMap:
    return deepcopy(modifiers)
