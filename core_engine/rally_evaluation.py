"""Complete rally-loadout evaluator: 9 leader skills + 4 joiner skills.

The service is intentionally an auditable combat-index model.  It does not
claim to reproduce Whiteout Survival's unpublished turn resolver.  Stable
buffs, probabilistic skills, and stateful/periodic skills are therefore shown
as three scenarios: deterministic floor, probability-weighted expectation,
and full-trigger ceiling.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import permutations
from math import prod
from typing import Any, Iterable, Mapping, Optional, Sequence

from hero_data import HEROES_BY_ID, TROOP_TYPES, ExpeditionSkill, Hero, get_hero
from core_engine.joiner_recommendation import (
    OBJECTIVE_PROFILES,
    CombatBuffs,
    CombatStats,
    calculate_balanced_score,
    calculate_counter_multiplier,
    normalize_troop_split,
)


COMBAT_FAQ_SOURCE = (
    "https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/"
    "8048-combat-faq/?l=en"
)
DUPLICATE_STACK_SOURCE = (
    "https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/"
    "8050-if-the-4-skills-of-the-rally-members-are-the-same-as-the-captain-s-will-the-effects-be-stackable/"
)
SUBJECT_DIFFERENCE_SOURCE = (
    "https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/"
    "8052-about-skill-descriptions/"
)
REPORT_VISIBILITY_SOURCE = (
    "https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/"
    "8051-what-special-bonuses-are-shown-in-battle-reports/"
)

SCENARIOS = ("floor", "expected", "ceiling")
MULTIPLIER_DAMAGE_EFFECTS = (
    "damage_up",
    "attack_damage_up",
)
EVENT_DAMAGE_EFFECTS = (
    "normal_attack_damage_up",
    "extra_attack_damage_up",
)
SCORED_EFFECTS = {
    "attack_up",
    "lethality_up",
    "defense_up",
    "health_up",
    "damage_taken_down",
    "enemy_damage_dealt_down",
    "enemy_damage_taken_up",
    "enemy_attack_down",
    "enemy_defense_down",
    "enemy_health_down",
    "enemy_lethality_down",
    *MULTIPLIER_DAMAGE_EFFECTS,
    *EVENT_DAMAGE_EFFECTS,
}
EPSILON = 1e-12
EXPECTED_FACTOR_MODEL_STATUSES = {
    "CHANCE_PROXY",
    "PERIODIC_PROXY",
    "DECAYING_SEQUENCE_PROXY",
    "EXTRA_ATTACK_PROXY",
    "PERIODIC_EVENT_PROXY",
    "STATEFUL_TRADEOFF",
}


def _read(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _leader_selection(value: Any) -> tuple[Hero, int]:
    hero_id = _read(value, "hero_id", _read(value, "heroId", _read(value, "id", "")))
    widget_level = _read(value, "widget_level", _read(value, "widgetLevel", 0))
    hero = get_hero(hero_id)
    if not hero:
        raise ValueError(f"Unknown rally leader hero: {hero_id!r}.")
    level = int(widget_level)
    if level < 0 or level > 10:
        raise ValueError(f"Widget level for {hero.name} must be between 0 and 10.")
    return hero, level


def _validate_leaders(values: Sequence[Any]) -> list[tuple[Hero, int]]:
    if len(values) != 3:
        raise ValueError("A complete rally leader march requires exactly 3 heroes.")
    selected = [_leader_selection(value) for value in values]
    heroes = [item[0] for item in selected]
    if len({hero.id for hero in heroes}) != 3:
        raise ValueError("Rally leader heroes must be unique.")
    if {hero.hero_type for hero in heroes} != set(TROOP_TYPES):
        raise ValueError("Rally leader march must contain exactly one Infantry, one Lancer, and one Marksman hero.")
    for hero in heroes:
        if hero.rarity != "mythic" or hero.generation not in range(1, 6):
            raise ValueError(f"{hero.name} is not an S1-S5 Mythic rally-leader candidate.")
        if sorted(skill.slot for skill in hero.expedition_skills) != [1, 2, 3]:
            raise ValueError(f"{hero.name} does not have all 3 researched Expedition skills configured.")
        if any(not skill.applicable_as_rally_leader for skill in hero.expedition_skills):
            raise ValueError(f"{hero.name} has a configured skill that is not valid for rally leadership.")
    return selected


def _validate_joiners(values: Sequence[Any]) -> list[Hero]:
    if len(values) != 4:
        raise ValueError("A complete rally requires exactly 4 contributing joiner heroes.")
    heroes: list[Hero] = []
    for value in values:
        hero = get_hero(value)
        if not hero:
            raise ValueError(f"Unknown rally joiner hero: {value!r}.")
        if not hero.primary_skill() or not hero.primary_skill().applicable_as_joiner:
            raise ValueError(f"{hero.name} has no configured first Expedition skill.")
        heroes.append(hero)
    return heroes


def _battle_context(objective: str) -> str:
    return "garrison" if objective in {"MAX_DEFENSE", "GARRISON_HOLD", "GARRISON_BALANCED"} else "pvp_attack"


def _scenario_factor(
    skill: ExpeditionSkill,
    scenario: str,
    context: str,
    include_disputed_skills: bool,
) -> tuple[float, str]:
    if context not in skill.combat_contexts:
        return 0.0, "context_excluded"
    if skill.model_status == "NON_COMBAT":
        return 0.0, "non_combat"
    if skill.experimental:
        if not include_disputed_skills:
            return 0.0, "disputed_excluded"
        if scenario == "ceiling":
            return 1.0, "experimental_ceiling_only"
        return 0.0, "experimental_not_guaranteed"
    conditional = bool(skill.activation_condition)
    if not conditional:
        return 1.0, "deterministic"
    if skill.model_status == "STATEFUL_UNBOUNDED":
        return 0.0, "unbounded_state_excluded"
    if scenario == "floor":
        return 0.0, "conditional_excluded"
    if scenario == "ceiling":
        return 1.0, "full_trigger"
    if (
        skill.activation_probability is None
        or skill.model_status not in EXPECTED_FACTOR_MODEL_STATUSES
    ):
        return 0.0, "expected_uptime_unknown"
    status = "expected_tradeoff_proxy" if skill.model_status == "STATEFUL_TRADEOFF" else "expected_proxy"
    return float(skill.activation_probability), status


def _component_dict(component: Any) -> dict[str, Any]:
    return {
        "effectType": component.effect_type,
        "valuePct": component.value_pct,
        "targetScope": component.target_scope,
        "sourceScope": getattr(component, "source_scope", "all_troops"),
        "affectedSide": component.affected_side,
        "stackingMethod": component.stacking_method,
        "canonicalStackKey": component.canonical_stack_key,
    }


def _skill_record(hero: Hero, skill: ExpeditionSkill, layer: str, instance: int) -> dict[str, Any]:
    return {
        "recordId": f"{layer}:{instance}:{hero.id}:{skill.slot}",
        "layer": layer,
        "heroId": hero.id,
        "heroName": hero.name,
        "heroType": hero.hero_type,
        "generation": hero.generation,
        "slot": skill.slot,
        "skillName": skill.name,
        "skillLevel": skill.skill_level,
        "effectType": skill.effect_type,
        "valuePct": skill.value_pct,
        "targetScope": skill.target_scope,
        "affectedSide": skill.affected_side,
        "conditional": bool(skill.activation_condition),
        "activationCondition": skill.activation_condition,
        "expectedFactor": skill.activation_probability,
        "durationTurns": skill.duration_turns,
        "intervalAttacks": skill.interval_attacks,
        "combatContexts": list(skill.combat_contexts),
        "modelStatus": skill.model_status,
        "modelNotes": skill.model_notes,
        "source": skill.source,
        "confidence": skill.confidence,
        "experimental": skill.experimental,
        "components": [_component_dict(component) for component in skill.resolved_components()],
        "_skill": skill,
    }


def _widget_record(hero: Hero, level: int, context: str) -> dict[str, Any]:
    widget = hero.widget
    value = widget.value_at_level(level)
    context_active = context in widget.combat_contexts
    active = bool(widget.supported and widget.effect_type and value > 0 and context_active)
    if level == 0:
        raw_selected: Optional[float] = 0.0
    elif level == 10:
        raw_selected = widget.raw_lethality_pct_at_level_10
    else:
        raw_selected = None
    return {
        "layer": "leader_widget",
        "heroId": hero.id,
        "heroName": hero.name,
        "heroType": hero.hero_type,
        "widgetName": widget.name,
        "widgetLevel": level,
        "expeditionSkillName": widget.expedition_skill_name,
        "effectType": widget.effect_type,
        "valuePct": value,
        "targetScope": widget.target_scope,
        "combatContexts": list(widget.combat_contexts),
        "activeForContext": active,
        "status": "active" if active else ("wrong_context" if value > 0 else "below_expedition_unlock"),
        "source": widget.source,
        "confidence": widget.confidence,
        "rawStats": {
            "scope": widget.raw_stat_scope,
            "selectedLevelValuePct": raw_selected,
            "selectedLevelLethalityPct": raw_selected,
            "selectedLevelHealthPct": (
                0.0 if level == 0 else widget.raw_health_pct_at_level_10 if level == 10 else None
            ),
            "level10LethalityPct": widget.raw_lethality_pct_at_level_10,
            "level10HealthPct": widget.raw_health_pct_at_level_10,
            "appliedToScore": False,
            "reason": (
                "Observed combat bonuses are assumed to include exclusive-gear raw stats. "
                "Authoritative intermediate level 1-9 values are unavailable, so the engine does not infer or double-count them."
            ),
        },
        "notes": widget.notes,
    }


def _component_applies(component: Mapping[str, Any], troop: str, enemy_troop: Optional[str]) -> bool:
    # sourceScope identifies the friendly class that triggers an effect; it
    # remains part of the audit/stack key but does not identify the benefited
    # row.  Ahmose Infantry, for example, can protect Lancers/Marksmen.
    target_scope = str(component.get("targetScope") or "all_troops")
    affected_side = str(component.get("affectedSide") or "friendly")
    subject = enemy_troop if affected_side == "enemy" else troop
    return target_scope == "all_troops" or target_scope == subject


def _resolved_buckets(
    skill_records: Sequence[Mapping[str, Any]],
    widget_records: Sequence[Mapping[str, Any]],
    scenario: str,
    context: str,
    troop: str,
    enemy_troop: Optional[str],
    include_disputed_skills: bool,
) -> tuple[dict[tuple[str, str, str, str, str], float], dict[str, float], list[str], list[dict[str, Any]]]:
    # Effects sharing an exact operational key add. Conditional records retain
    # their identity for audit, while scenario-weighted magnitudes are grouped
    # later without inventing a summed proc probability.
    buckets: dict[tuple[str, str, str, str, str], float] = defaultdict(float)
    widget_special: dict[str, float] = defaultdict(float)
    warnings: list[str] = []
    applied: list[dict[str, Any]] = []
    for record in skill_records:
        skill: ExpeditionSkill = record["_skill"]
        factor, status = _scenario_factor(skill, scenario, context, include_disputed_skills)
        if status in {
            "expected_uptime_unknown",
            "disputed_excluded",
            "unbounded_state_excluded",
            "experimental_not_guaranteed",
        }:
            warnings.append(f"{record['heroName']} / {record['skillName']}: {status.replace('_', ' ')}.")
        if status == "expected_tradeoff_proxy":
            warnings.append(
                f"{record['heroName']} / {record['skillName']}: defensive uptime is modeled, "
                "but its skipped-attack tradeoff is not priced."
            )
        record_applied = False
        for component in record["components"]:
            if factor <= 0 or component["effectType"] not in SCORED_EFFECTS:
                continue
            if str(component.get("stackingMethod") or "ADDITIVE").upper() != "ADDITIVE":
                raise ValueError(
                    f"Unsupported stacking method for {record['heroName']} / {record['skillName']}: "
                    f"{component['stackingMethod']}."
                )
            if not _component_applies(component, troop, enemy_troop):
                continue
            conditional_id = record["recordId"] if record["conditional"] else "deterministic"
            key = (
                component["affectedSide"],
                component["targetScope"],
                component["sourceScope"],
                component["effectType"],
                conditional_id,
            )
            buckets[key] += float(component["valuePct"]) / 100.0 * factor
            record_applied = True
        if record_applied:
            applied.append({"recordId": record["recordId"], "status": status, "factor": factor})
    for widget in widget_records:
        if not widget["activeForContext"]:
            continue
        effect_type = widget.get("effectType")
        if effect_type not in SCORED_EFFECTS:
            continue
        widget_special[str(effect_type)] += float(widget["valuePct"]) / 100.0
        applied.append({"recordId": f"widget:{widget['heroId']}", "status": "active_special", "factor": 1.0})
    return dict(buckets), dict(widget_special), warnings, applied


def _bucket_factor(
    buckets: Mapping[tuple[str, str, str, str, str], float],
    effect_type: str,
    existing_all_troop: float = 0.0,
) -> float:
    # Conditional instances retain record IDs in the audit rows, but values
    # sharing the same operational side/scope/effect still add in one buff
    # category.  This stacks probability-weighted contributions without ever
    # turning four 40% proc skills into a fictional 160% proc chance.
    grouped: dict[tuple[str, str, str, str], float] = defaultdict(float)
    for key, value in buckets.items():
        if key[3] == effect_type:
            grouped[key[:4]] += float(value)
    factor = 1.0
    existing_applied = False
    expected_side = "enemy" if effect_type.startswith("enemy_") else "friendly"
    for key, value in grouped.items():
        bucket_value = float(value)
        if key == (expected_side, "all_troops", "all_troops", effect_type):
            bucket_value += float(existing_all_troop)
            existing_applied = True
        factor *= 1.0 + bucket_value
    if not existing_applied:
        factor *= 1.0 + float(existing_all_troop)
    return factor


def _event_channel_factor(
    buckets: Mapping[tuple[str, str, str, str, str], float],
) -> float:
    """Combine normal/extra attack event contributions without nesting them.

    Public descriptions do not establish that one extra-attack event amplifies
    another.  Their scenario-weighted magnitudes therefore add to the event
    channel instead of multiplying as if every event always contained every
    other event.
    """

    return 1.0 + sum(
        float(value)
        for key, value in buckets.items()
        if key[3] in EVENT_DAMAGE_EFFECTS
    )


def _score_troop(
    base_stats: CombatStats,
    buffs: CombatBuffs,
    buckets: Mapping[tuple[str, str, str, str, str], float],
    widget_special: Mapping[str, float],
    troop: str,
    enemy_troop: Optional[str],
    enemy_stats: Optional[CombatStats],
    scenario: str = "floor",
) -> dict[str, Any]:
    attack_factor = _bucket_factor(buckets, "attack_up", buffs.attack) * (1.0 + widget_special.get("attack_up", 0.0))
    lethality_factor = _bucket_factor(buckets, "lethality_up", buffs.lethality) * (1.0 + widget_special.get("lethality_up", 0.0))
    defense_factor = _bucket_factor(buckets, "defense_up", buffs.defense) * (1.0 + widget_special.get("defense_up", 0.0))
    health_factor = _bucket_factor(buckets, "health_up", buffs.health) * (1.0 + widget_special.get("health_up", 0.0))
    damage_factors = [_bucket_factor(buckets, "damage_up", buffs.damage_dealt)]
    damage_factors.append(_bucket_factor(buckets, "attack_damage_up"))
    event_channel_factor = _event_channel_factor(buckets)
    damage_factors.append(event_channel_factor)
    damage_factors.append(_bucket_factor(buckets, "enemy_damage_taken_up"))
    counter = calculate_counter_multiplier(troop, enemy_troop)
    damage = (base_stats.attack * attack_factor * base_stats.lethality * lethality_factor) / 100.0
    damage *= prod(damage_factors) * counter

    enemy_penetration_factor = 1.0
    if enemy_stats is not None:
        defense_reduction = max(0.0, _bucket_factor(buckets, "enemy_defense_down") - 1.0)
        health_reduction = max(0.0, _bucket_factor(buckets, "enemy_health_down") - 1.0)
        adjusted_enemy_defense = max(0.0, enemy_stats.defense * (1.0 - defense_reduction))
        adjusted_enemy_health = max(0.0, enemy_stats.health * (1.0 - health_reduction))
        enemy_penetration_factor = (
            (100.0 + enemy_stats.defense) / max(EPSILON, 100.0 + adjusted_enemy_defense)
        ) * (
            (100.0 + enemy_stats.health) / max(EPSILON, 100.0 + adjusted_enemy_health)
        )
        damage *= enemy_penetration_factor

    base_defense = (base_stats.defense * defense_factor * base_stats.health * health_factor) / 100.0
    reduction_factors = {
        "damageTaken": _bucket_factor(buckets, "damage_taken_down", buffs.damage_taken_reduction),
        "enemyDamageDealt": _bucket_factor(buckets, "enemy_damage_dealt_down"),
        "enemyAttack": _bucket_factor(buckets, "enemy_attack_down"),
        "enemyLethality": _bucket_factor(buckets, "enemy_lethality_down"),
    }
    reciprocal_reduction = prod(reduction_factors.values())
    defense = base_defense * reciprocal_reduction
    has_conditional_reduction = any(
        key[4] != "deterministic"
        and key[3] in {
            "damage_taken_down",
            "enemy_damage_dealt_down",
            "enemy_attack_down",
            "enemy_lethality_down",
        }
        for key in buckets
    )
    incoming_damage_proxy = 1.0 / max(EPSILON, reciprocal_reduction)
    return {
        "damageScore": damage,
        "defenseScore": defense,
        "counterMultiplier": counter,
        "effectiveAttack": base_stats.attack * attack_factor,
        "effectiveLethality": base_stats.lethality * lethality_factor,
        "effectiveDefense": base_stats.defense * defense_factor,
        "effectiveHealth": base_stats.health * health_factor,
        "damageLayerFactor": prod(damage_factors),
        "eventDamageChannelFactor": event_channel_factor,
        "widgetSpecialFactors": {key: 1.0 + value for key, value in widget_special.items()},
        "reciprocalReductionFactor": reciprocal_reduction,
        "incomingDamageMultiplier": (
            None if scenario == "expected" and has_conditional_reduction else incoming_damage_proxy
        ),
        "incomingDamageMultiplierProxy": incoming_damage_proxy,
        "expectedDefenseIndexProxy": scenario == "expected" and has_conditional_reduction,
        "enemyPenetrationFactor": enemy_penetration_factor,
        "reductionFactors": reduction_factors,
    }


def _scenario_score(
    skill_records: Sequence[Mapping[str, Any]],
    widget_records: Sequence[Mapping[str, Any]],
    scenario: str,
    context: str,
    base_stats: CombatStats,
    buffs: CombatBuffs,
    split: Mapping[str, float],
    target_troop: str,
    enemy_troop: Optional[str],
    enemy_stats: Optional[CombatStats],
    attack_weight: float,
    defense_weight: float,
    include_disputed_skills: bool,
) -> dict[str, Any]:
    troops = set(split) | {target_troop}
    per_troop: dict[str, Any] = {}
    warnings: list[str] = []
    applied_ids: set[str] = set()
    bucket_rows: list[dict[str, Any]] = []
    for troop in sorted(troops):
        buckets, widget_special, troop_warnings, applied = _resolved_buckets(
            skill_records, widget_records, scenario, context, troop, enemy_troop, include_disputed_skills
        )
        warnings.extend(troop_warnings)
        applied_ids.update(item["recordId"] for item in applied)
        scored = _score_troop(
            base_stats, buffs, buckets, widget_special, troop, enemy_troop, enemy_stats, scenario
        )
        per_troop[troop] = scored
        if scored["expectedDefenseIndexProxy"]:
            warnings.append(
                "Conditional defense is a probability-weighted reciprocal-index proxy; "
                "an expected incoming-damage probability is not asserted."
            )
        for key, value in sorted(buckets.items()):
            bucket_rows.append({
                "troop": troop,
                "affectedSide": key[0],
                "targetScope": key[1],
                "sourceScope": key[2],
                "effectType": key[3],
                "conditionalRecord": None if key[4] == "deterministic" else key[4],
                "combinedPct": value * 100.0,
            })

    before_per_troop = {
        troop: _score_troop(base_stats, buffs, {}, {}, troop, enemy_troop, enemy_stats, "floor")
        for troop in troops
    }

    def weighted(source: Mapping[str, Any], key: str) -> float:
        return sum(float(split[troop]) * float(source[troop][key]) for troop in split)

    damage_before = weighted(before_per_troop, "damageScore")
    damage_after = weighted(per_troop, "damageScore")
    defense_before = weighted(before_per_troop, "defenseScore")
    defense_after = weighted(per_troop, "defenseScore")
    damage_ratio = damage_after / max(EPSILON, damage_before)
    defense_ratio = defense_after / max(EPSILON, defense_before)
    target_damage_before = before_per_troop[target_troop]["damageScore"]
    target_damage_after = per_troop[target_troop]["damageScore"]
    target_ratio = target_damage_after / max(EPSILON, target_damage_before)
    balanced = calculate_balanced_score(damage_ratio, defense_ratio, attack_weight, defense_weight)
    return {
        "damageScoreBefore": damage_before,
        "damageScoreAfter": damage_after,
        "damageImprovementPct": (damage_ratio - 1.0) * 100.0,
        "targetDamageScoreBefore": target_damage_before,
        "targetDamageScoreAfter": target_damage_after,
        "targetDamageImprovementPct": (target_ratio - 1.0) * 100.0,
        "defenseScoreBefore": defense_before,
        "defenseScoreAfter": defense_after,
        "defenseImprovementPct": (defense_ratio - 1.0) * 100.0,
        "damageRatio": damage_ratio,
        "targetDamageRatio": target_ratio,
        "defenseRatio": defense_ratio,
        "balancedScore": balanced,
        "appliedRecordCount": len(applied_ids),
        "appliedRecordIds": sorted(applied_ids),
        "stackBuckets": bucket_rows,
        "warnings": sorted(set(warnings)),
        "perTroop": per_troop,
    }


def _goal_ratio(objective: str, score: Mapping[str, Any]) -> float:
    if objective in {"KILL_INFANTRY", "KILL_LANCERS", "KILL_MARKSMEN"}:
        return float(score["targetDamageRatio"])
    if objective in {"MAX_DEFENSE", "GARRISON_HOLD"}:
        return float(score["defenseRatio"])
    if objective == "MAX_DAMAGE":
        return float(score["damageRatio"])
    return float(score["balancedScore"])


def _inventory_lineups(
    hero_ids: Sequence[str],
    available_counts: Mapping[str, int],
    slots: int = 4,
) -> list[tuple[str, ...]]:
    """Enumerate inventory-valid lineups in caller-supplied hero priority order."""

    generated: list[tuple[str, ...]] = []

    def visit(index: int, remaining: int, selected: list[str]) -> None:
        if remaining == 0:
            generated.append(tuple(selected))
            return
        if index >= len(hero_ids):
            return
        hero_id = hero_ids[index]
        limit = min(remaining, max(0, int(available_counts.get(hero_id, 0))))
        for count in range(limit, -1, -1):
            visit(index + 1, remaining - count, selected + [hero_id] * count)

    visit(0, slots, [])
    return generated


def _plan_state_is_better(candidate: Mapping[str, Any], incumbent: Optional[Mapping[str, Any]]) -> bool:
    """Compare DP states with stable, input-order tie resolution."""

    if incumbent is None:
        return True
    if candidate["completed"] != incumbent["completed"]:
        return int(candidate["completed"]) > int(incumbent["completed"])
    score_delta = float(candidate["weighted_score"]) - float(incumbent["weighted_score"])
    if abs(score_delta) > EPSILON:
        return score_delta > 0
    return tuple(candidate["tie_signature"]) > tuple(incumbent["tie_signature"])


class RallyEvaluationService:
    """Evaluate one fully specified S1-S5 rally or garrison loadout."""

    def evaluate(
        self,
        objective: str,
        leader_heroes: Sequence[Any],
        joiner_hero_ids: Sequence[Any],
        troop_type: str = "infantry",
        enemy_troop_type: Optional[str] = None,
        base_stats: Optional[CombatStats] = None,
        current_buffs: Optional[CombatBuffs] = None,
        enemy_stats: Optional[CombatStats] = None,
        troop_split: Optional[Mapping[str, float]] = None,
        include_disputed_skills: bool = False,
    ) -> dict[str, Any]:
        if objective not in OBJECTIVE_PROFILES:
            raise ValueError(f"Unsupported rally objective: {objective}.")
        if troop_type not in TROOP_TYPES:
            raise ValueError("Troop type must be infantry, lancer, or marksman.")
        if enemy_troop_type is not None and enemy_troop_type not in TROOP_TYPES:
            raise ValueError("Enemy troop type must be infantry, lancer, or marksman.")
        selected_leaders = _validate_leaders(list(leader_heroes))
        joiners = _validate_joiners(list(joiner_hero_ids))
        profile = OBJECTIVE_PROFILES[objective]
        target_troop = str(profile.get("counter_troop") or troop_type)
        resolved_enemy = profile.get("enemy_troop") or enemy_troop_type
        context = _battle_context(objective)
        split = normalize_troop_split(troop_split, target_troop)
        stats = base_stats or CombatStats()
        buffs = current_buffs or CombatBuffs()
        attack_weight = float(profile.get("attack_weight", 0.5))
        defense_weight = float(profile.get("defense_weight", 0.5))

        leader_records: list[dict[str, Any]] = []
        for instance, (hero, _) in enumerate(selected_leaders):
            for expedition_skill in sorted(hero.expedition_skills, key=lambda item: item.slot):
                leader_records.append(_skill_record(hero, expedition_skill, "leader_skill", instance))
        joiner_records = [
            _skill_record(hero, hero.primary_skill(), "joiner_primary", instance)
            for instance, hero in enumerate(joiners)
            if hero.primary_skill() is not None
        ]
        widget_records = [_widget_record(hero, level, context) for hero, level in selected_leaders]
        all_skill_records = leader_records + joiner_records

        scenario_scores = {
            scenario: _scenario_score(
                all_skill_records,
                widget_records,
                scenario,
                context,
                stats,
                buffs,
                split,
                target_troop,
                resolved_enemy,
                enemy_stats,
                attack_weight,
                defense_weight,
                include_disputed_skills,
            )
            for scenario in SCENARIOS
        }
        ratios = {scenario: _goal_ratio(objective, score) for scenario, score in scenario_scores.items()}
        floor_lift = (ratios["floor"] - 1.0) * 100.0
        expected_lift = (ratios["expected"] - 1.0) * 100.0
        ceiling_lift = (ratios["ceiling"] - 1.0) * 100.0
        if floor_lift > 1e-9:
            assessment_status = "DETERMINISTIC_SUPPORT"
        elif expected_lift > 1e-9:
            assessment_status = "CONDITIONAL_ONLY"
        elif ceiling_lift > 1e-9:
            assessment_status = "CEILING_ONLY"
        else:
            assessment_status = "NO_MODELED_LIFT"

        warnings: list[str] = []
        for score in scenario_scores.values():
            warnings.extend(score["warnings"])
        for record in all_skill_records:
            if record["modelStatus"] not in {"DIRECT", "CONTEXT_ONLY", "NON_COMBAT"}:
                warnings.append(
                    f"{record['heroName']} / {record['skillName']} uses {record['modelStatus'].lower().replace('_', ' ')}; "
                    "floor/expected/ceiling are scenario indices, not a turn-by-turn guarantee."
                )
        if any(record["experimental"] for record in all_skill_records) and not include_disputed_skills:
            warnings.append("Disputed tooltip effects are listed but excluded from numerical scoring.")
        elif any(record["experimental"] for record in all_skill_records):
            warnings.append(
                "Disputed tooltip effects are enabled for the ceiling scenario only; they remain excluded "
                "from the deterministic floor and expected proxy."
            )

        context_eligible = [
            record
            for record in all_skill_records
            if context in record["combatContexts"] and record["modelStatus"] != "NON_COMBAT"
        ]
        experimental_excluded = [
            record
            for record in context_eligible
            if record["experimental"] and not include_disputed_skills
        ]
        experimental_ceiling_only = [
            record
            for record in context_eligible
            if record["experimental"] and include_disputed_skills
        ]
        scoring_eligible = [
            record
            for record in context_eligible
            if record not in experimental_excluded and record not in experimental_ceiling_only
        ]
        expected_modeled = [
            record
            for record in scoring_eligible
            if record["conditional"]
            and record["expectedFactor"] is not None
            and record["modelStatus"] in EXPECTED_FACTOR_MODEL_STATUSES
        ]
        expected_unknown = [
            record
            for record in scoring_eligible
            if record["conditional"] and record not in expected_modeled
        ]
        unsupported_effect_records = [
            record
            for record in scoring_eligible
            if not any(component["effectType"] in SCORED_EFFECTS for component in record["components"])
        ]
        tradeoff_records = [
            record for record in scoring_eligible if record["modelStatus"] == "STATEFUL_TRADEOFF"
        ]
        combat_model_complete = not (
            experimental_excluded
            or experimental_ceiling_only
            or expected_unknown
            or unsupported_effect_records
            or tradeoff_records
        )

        def public_skill(record: Mapping[str, Any]) -> dict[str, Any]:
            return {key: value for key, value in record.items() if key != "_skill"}

        return {
            "objective": objective,
            "calculationKind": "NORMALIZED_SKILL_STACK_INDEX",
            "battleContext": context,
            "targetTroopType": target_troop,
            "enemyTroopType": resolved_enemy,
            "formationTroopSplit": split,
            "contract": {
                "leaderHeroCount": len(selected_leaders),
                "leaderSkillSlots": len(leader_records),
                "requiredLeaderSkillSlots": 9,
                "joinerContributionSlots": len(joiner_records),
                "requiredJoinerContributionSlots": 4,
                "leaderWidgetCount": len(widget_records),
                "joinerWidgetsApplied": 0,
                "complete": len(leader_records) == 9 and len(joiner_records) == 4,
                "completeMeaning": "STRUCTURAL_9_LEADER_SKILLS_PLUS_4_JOINER_PRIMARY_SKILLS",
                "ruleSource": COMBAT_FAQ_SOURCE,
            },
            "leaderHeroes": [
                {
                    "heroId": hero.id,
                    "heroName": hero.name,
                    "heroType": hero.hero_type,
                    "generation": hero.generation,
                    "widgetLevel": level,
                    "maxExpeditionAttackPct": hero.max_expedition_attack_pct,
                    "maxExpeditionDefensePct": hero.max_expedition_defense_pct,
                    "baseStatsAppliedToScore": False,
                    "baseStatsNote": "Observed combat bonuses are the baseline; max hero stats are shown for audit and are not added again.",
                }
                for hero, level in selected_leaders
            ],
            "leaderSkills": [public_skill(record) for record in leader_records],
            "joinerSkills": [public_skill(record) for record in joiner_records],
            "widgets": widget_records,
            "modelCoverage": {
                "totalSkillSlots": len(all_skill_records),
                "contextEligibleSkillSlots": len(context_eligible),
                "numericallyEligibleSkillSlots": len(scoring_eligible),
                "experimentalExcludedSlots": len(experimental_excluded),
                "experimentalExcludedRecordIds": [
                    record["recordId"] for record in experimental_excluded
                ],
                "experimentalCeilingOnlySlots": len(experimental_ceiling_only),
                "experimentalCeilingOnlyRecordIds": [
                    record["recordId"] for record in experimental_ceiling_only
                ],
                "deterministicContextEligibleSlots": sum(
                    1 for record in scoring_eligible if not record["conditional"]
                ),
                "expectedConditionalModeledSlots": len(expected_modeled),
                "expectedConditionalUnknownSlots": len(expected_unknown),
                "expectedConditionalUnknownRecordIds": [record["recordId"] for record in expected_unknown],
                "unsupportedEffectSlots": len(unsupported_effect_records),
                "unscoredSkills": [
                    {
                        "recordId": record["recordId"],
                        "heroName": record["heroName"],
                        "skillName": record["skillName"],
                        "effectTypes": [component["effectType"] for component in record["components"]],
                        "reason": "The current normalized equation has no validated channel for this mechanic.",
                    }
                    for record in unsupported_effect_records
                ],
                "unpricedTradeoffRecordIds": [record["recordId"] for record in tradeoff_records],
                "combatModelComplete": combat_model_complete,
                "contractCompleteDoesNotImplyExactCombatModel": True,
            },
            "scenarios": scenario_scores,
            "goalAssessment": {
                "status": assessment_status,
                "completeContract": len(leader_records) == 9 and len(joiner_records) == 4,
                "floorLiftPct": floor_lift,
                "expectedLiftPct": expected_lift,
                "ceilingLiftPct": ceiling_lift,
                "explanation": (
                    "Deterministic support means the verified always-on layers improve the selected goal before any proc. "
                    "Conditional-only means a supported probability proxy improves it. Ceiling-only means any modeled "
                    "upside depends entirely on unresolved timing, state, or an explicitly enabled disputed tooltip."
                ),
            },
            "scenarioPolicy": {
                "floor": "Verified always-on effects only; conditional, periodic, and chance skills contribute zero.",
                "expected": (
                    "Probability-weighted explanatory proxy where a supported chance or nominal uptime is known; "
                    "unknown uptime contributes zero and independence is not claimed as a hidden game rule."
                ),
                "ceiling": (
                    "All eligible conditional effects are shown at full trigger simultaneously. This is a stress-test "
                    "upper scenario, not a probability forecast or promised battle result."
                ),
            },
            "stackingPolicy": {
                "sameOperationalKey": "ADD",
                "differentScopeOrEffect": "MULTIPLY_AS_DISTINCT_EQUATION_LAYERS",
                "conditionalDuplicates": (
                    "KEEP PROC RECORDS SEPARATE; ADD SCENARIO-WEIGHTED MAGNITUDES WITHIN THE SAME "
                    "OPERATIONAL BUCKET; DO NOT SUM PROC CHANCE"
                ),
                "normalAndExtraAttackEvents": (
                    "ADD SCENARIO-WEIGHTED EVENT CONTRIBUTIONS INSIDE ONE EVENT-DAMAGE CHANNEL; "
                    "DO NOT ASSUME EVENTS AMPLIFY ONE ANOTHER"
                ),
                "widgetSpecial": "ADD WITHIN SPECIAL CATEGORY, THEN MULTIPLY THE OBSERVED ORDINARY STAT",
                "defenseReductionModel": "COMMUNITY_RECIPROCAL_INDEX",
                "officialDuplicateSource": DUPLICATE_STACK_SOURCE,
                "officialDifferentSubjectSource": SUBJECT_DIFFERENCE_SOURCE,
            },
            "reportPolicy": {
                "observedStatsAssumedToIncludeHeroAndExclusiveGearRawStats": True,
                "sharedObservedStatVectorAcrossTroops": True,
                "sharedStatVectorMeaning": (
                    "The current request supplies one Attack/Defense/Health/Lethality vector for the formation. "
                    "When actual report stats differ by troop class, scenario outputs are normalized skill-stack "
                    "indices rather than a casualty or exact damage forecast."
                ),
                "heroSkillEffectsCalculatedInBattle": True,
                "source": REPORT_VISIBILITY_SOURCE,
            },
            "warnings": sorted(set(warnings)),
        }

    def _rank_complete_joiner_lineups(
        self,
        rally: Mapping[str, Any],
        available_hero_ids: Sequence[str],
        available_hero_counts: Mapping[str, int],
    ) -> list[dict[str, Any]]:
        """Rank four-joiner lineups only after evaluating the complete 9+4 stack."""

        objective = str(rally.get("objective") or "")
        if objective not in OBJECTIVE_PROFILES:
            raise ValueError(f"Unsupported rally objective: {objective}.")
        troop_type = str(rally.get("troop_type") or "infantry")
        enemy_troop_type = rally.get("enemy_troop_type")
        if troop_type not in TROOP_TYPES:
            raise ValueError("Troop type must be infantry, lancer, or marksman.")
        if enemy_troop_type is not None and enemy_troop_type not in TROOP_TYPES:
            raise ValueError("Enemy troop type must be infantry, lancer, or marksman.")
        selected_leaders = _validate_leaders(list(rally.get("leader_heroes") or []))
        profile = OBJECTIVE_PROFILES[objective]
        target_troop = str(profile.get("counter_troop") or troop_type)
        resolved_enemy = profile.get("enemy_troop") or enemy_troop_type
        context = _battle_context(objective)
        split = normalize_troop_split(rally.get("troop_split"), target_troop)
        stats = rally.get("base_stats") or CombatStats()
        buffs = rally.get("current_buffs") or CombatBuffs()
        enemy_stats = rally.get("enemy_stats")
        attack_weight = float(profile.get("attack_weight", 0.5))
        defense_weight = float(profile.get("defense_weight", 0.5))
        include_disputed = bool(rally.get("include_disputed_skills", False))

        leader_records: list[dict[str, Any]] = []
        for instance, (hero, _) in enumerate(selected_leaders):
            for expedition_skill in sorted(hero.expedition_skills, key=lambda item: item.slot):
                leader_records.append(_skill_record(hero, expedition_skill, "leader_skill", instance))
        widget_records = [_widget_record(hero, level, context) for hero, level in selected_leaders]
        eligible_ids: list[str] = []
        for hero_id in available_hero_ids:
            hero = get_hero(hero_id)
            primary = hero.primary_skill() if hero else None
            if not hero or not primary or not primary.applicable_as_joiner:
                continue
            if primary.experimental and not include_disputed:
                continue
            eligible_ids.append(hero_id)
        lineups = _inventory_lineups(eligible_ids, available_hero_counts, 4)

        score_troops = (
            (target_troop,)
            if objective in {"KILL_INFANTRY", "KILL_LANCERS", "KILL_MARKSMEN"}
            else tuple(troop for troop, weight in split.items() if float(weight) > 0)
        )
        baselines = {
            troop: _score_troop(
                stats,
                buffs,
                {},
                {},
                troop,
                resolved_enemy,
                enemy_stats,
                "floor",
            )
            for troop in score_troops
        }
        fixed_buckets: dict[str, dict[str, dict[tuple[str, str, str, str, str], float]]] = {}
        fixed_widgets: dict[str, dict[str, dict[str, float]]] = {}
        hero_deltas: dict[str, dict[str, dict[str, dict[tuple[str, str, str, str, str], float]]]] = {}
        for scenario in SCENARIOS:
            fixed_buckets[scenario] = {}
            fixed_widgets[scenario] = {}
            for troop in score_troops:
                buckets, widgets, _, _ = _resolved_buckets(
                    leader_records,
                    widget_records,
                    scenario,
                    context,
                    troop,
                    resolved_enemy,
                    include_disputed,
                )
                fixed_buckets[scenario][troop] = buckets
                fixed_widgets[scenario][troop] = widgets
            hero_deltas[scenario] = {}
            for hero_id in eligible_ids:
                hero = get_hero(hero_id)
                primary = hero.primary_skill()
                record = _skill_record(hero, primary, "joiner_primary", 0)
                hero_deltas[scenario][hero_id] = {}
                for troop in score_troops:
                    delta, _, _, _ = _resolved_buckets(
                        [record],
                        [],
                        scenario,
                        context,
                        troop,
                        resolved_enemy,
                        include_disputed,
                    )
                    hero_deltas[scenario][hero_id][troop] = delta

        def lineup_goal_ratio(hero_ids: Sequence[str], scenario: str) -> float:
            scored: dict[str, Mapping[str, Any]] = {}
            for troop in score_troops:
                buckets = dict(fixed_buckets[scenario][troop])
                for hero_id in hero_ids:
                    for key, value in hero_deltas[scenario][hero_id][troop].items():
                        buckets[key] = buckets.get(key, 0.0) + float(value)
                scored[troop] = _score_troop(
                    stats,
                    buffs,
                    buckets,
                    fixed_widgets[scenario][troop],
                    troop,
                    resolved_enemy,
                    enemy_stats,
                    scenario,
                )
            if objective in {"KILL_INFANTRY", "KILL_LANCERS", "KILL_MARKSMEN"}:
                return float(scored[target_troop]["damageScore"]) / max(
                    EPSILON,
                    float(baselines[target_troop]["damageScore"]),
                )

            def weighted(source: Mapping[str, Mapping[str, Any]], key: str) -> float:
                return sum(float(split[troop]) * float(source[troop][key]) for troop in score_troops)

            damage_ratio = weighted(scored, "damageScore") / max(
                EPSILON,
                weighted(baselines, "damageScore"),
            )
            defense_ratio = weighted(scored, "defenseScore") / max(
                EPSILON,
                weighted(baselines, "defenseScore"),
            )
            if objective in {"MAX_DEFENSE", "GARRISON_HOLD"}:
                return defense_ratio
            if objective == "MAX_DAMAGE":
                return damage_ratio
            return calculate_balanced_score(damage_ratio, defense_ratio, attack_weight, defense_weight)

        ranked: list[dict[str, Any]] = []
        for order, hero_ids in enumerate(lineups):
            ranked.append({
                "hero_ids": hero_ids,
                "usage": Counter(hero_ids),
                "floor_lift_pct": (lineup_goal_ratio(hero_ids, "floor") - 1.0) * 100.0,
                "expected_lift_pct": (lineup_goal_ratio(hero_ids, "expected") - 1.0) * 100.0,
                "ceiling_lift_pct": (lineup_goal_ratio(hero_ids, "ceiling") - 1.0) * 100.0,
                "order": order,
            })
        # Python's stable sort deliberately preserves available_hero_ids order
        # for mathematically identical skills (Jessie/Jasser, Lumak/Ling).
        ranked.sort(key=lambda item: (
            -item["expected_lift_pct"],
            -item["floor_lift_pct"],
            -item["ceiling_lift_pct"],
        ))
        return ranked

    def optimize_plan(
        self,
        rallies: Sequence[Mapping[str, Any]],
        available_hero_ids: Sequence[str],
        available_hero_counts: Optional[Mapping[str, int]] = None,
        alternative_count: int = 2,
    ) -> dict[str, Any]:
        """Globally allocate inventory by the complete expected 9+4 goal lift.

        The exact inventory search first maximizes the number of structurally complete
        rallies, then maximizes their summed priority-weighted expected goal
        lift. It never ranks joiners in isolation from leader skills/widgets.
        """

        if not rallies:
            raise ValueError("At least one rally is required for plan optimization.")
        ordered_ids: list[str] = []
        seen: set[str] = set()
        for raw_hero_id in available_hero_ids:
            hero_id = str(raw_hero_id).lower()
            if hero_id in seen:
                raise ValueError(f"Available joiner hero IDs must be unique: {hero_id}.")
            hero = get_hero(hero_id)
            if not hero or not hero.primary_skill() or not hero.primary_skill().applicable_as_joiner:
                raise ValueError(f"Unknown or ineligible rally joiner hero: {hero_id}.")
            seen.add(hero_id)
            ordered_ids.append(hero_id)
        if not ordered_ids:
            raise ValueError("At least one eligible rally joiner hero is required.")
        raw_counts = available_hero_counts or {}
        counts = {
            hero_id: max(0, int(raw_counts.get(hero_id, 1 if not raw_counts else 0)))
            for hero_id in ordered_ids
        }
        if any(int(value) < 0 for value in raw_counts.values()):
            raise ValueError("Available hero counts cannot be negative.")
        if alternative_count < 0:
            raise ValueError("Alternative count cannot be negative.")

        normalized_rallies: list[dict[str, Any]] = []
        rally_ids: set[str] = set()
        rankings: list[list[dict[str, Any]]] = []
        ranking_cache: dict[str, list[dict[str, Any]]] = {}
        for index, raw_rally in enumerate(rallies):
            rally = dict(raw_rally)
            rally_id = str(rally.pop("rally_id", index))
            if rally_id in rally_ids:
                raise ValueError(f"Rally IDs must be unique: {rally_id}.")
            rally_ids.add(rally_id)
            priority_weight = float(rally.pop("priority_weight", 1.0))
            if priority_weight <= 0:
                raise ValueError("Rally priority weights must be positive.")
            rally["rally_id"] = rally_id
            rally["priority_weight"] = priority_weight
            normalized_rallies.append(rally)
            ranking_key = repr({
                key: value
                for key, value in rally.items()
                if key not in {"rally_id", "priority_weight"}
            })
            if ranking_key not in ranking_cache:
                ranking_cache[ranking_key] = self._rank_complete_joiner_lineups(rally, ordered_ids, counts)
            rankings.append(ranking_cache[ranking_key])

        initial_remaining = tuple(counts[hero_id] for hero_id in ordered_ids)
        weighted_rankings: list[list[dict[str, Any]]] = []
        for rally, ranked in zip(normalized_rallies, rankings):
            priority_weight = float(rally["priority_weight"])
            weighted_rankings.append([
                {
                    **candidate,
                    "weighted_lift_pct": float(candidate["expected_lift_pct"]) * priority_weight,
                    "usage_tuple": tuple(
                        int(candidate["usage"].get(hero_id, 0)) for hero_id in ordered_ids
                    ),
                }
                for candidate in ranked
            ])

        availability_masks: list[list[list[int]]] = []
        for ranked in weighted_rankings:
            per_hero: list[list[int]] = []
            for hero_index in range(len(ordered_ids)):
                limits: list[int] = []
                for available in range(5):
                    mask = 0
                    for rank, candidate in enumerate(ranked):
                        if int(candidate["usage_tuple"][hero_index]) <= available:
                            mask |= 1 << rank
                    limits.append(mask)
                per_hero.append(limits)
            availability_masks.append(per_hero)

        def valid_candidate_mask(rally_index: int, remaining: tuple[int, ...]) -> int:
            ranked = weighted_rankings[rally_index]
            mask = (1 << len(ranked)) - 1
            for hero_index, available in enumerate(remaining):
                mask &= availability_masks[rally_index][hero_index][min(4, max(0, available))]
                if not mask:
                    break
            return mask

        input_rally_order = {
            rally["rally_id"]: index for index, rally in enumerate(normalized_rallies)
        }
        best_order = tuple(range(len(normalized_rallies)))
        if len(normalized_rallies) <= 7 and sum(counts.values()) >= 4 * len(normalized_rallies):
            best_order_score = float("-inf")
            for rally_order in permutations(range(len(normalized_rallies))):
                greedy_remaining = tuple(counts[hero_id] for hero_id in ordered_ids)
                greedy_score = 0.0
                feasible = True
                for rally_index in rally_order:
                    valid_mask = valid_candidate_mask(rally_index, greedy_remaining)
                    if not valid_mask:
                        feasible = False
                        break
                    selected_rank = (valid_mask & -valid_mask).bit_length() - 1
                    candidate = weighted_rankings[rally_index][selected_rank]
                    greedy_score += float(candidate["weighted_lift_pct"])
                    greedy_remaining = tuple(
                        available - required
                        for available, required in zip(greedy_remaining, candidate["usage_tuple"])
                    )
                if feasible and greedy_score > best_order_score + EPSILON:
                    best_order = rally_order
                    best_order_score = greedy_score
        if best_order != tuple(range(len(normalized_rallies))):
            normalized_rallies = [normalized_rallies[index] for index in best_order]
            rankings = [rankings[index] for index in best_order]
            weighted_rankings = [weighted_rankings[index] for index in best_order]
            availability_masks = [availability_masks[index] for index in best_order]

        requested_completions = min(
            len(normalized_rallies),
            sum(initial_remaining) // 4,
            sum(1 for ranked in weighted_rankings if ranked),
        )
        winner_state: Optional[dict[str, Any]] = None
        search_nodes = 0
        for target_completions in range(requested_completions, -1, -1):
            incumbent: Optional[dict[str, Any]] = None
            seen_scores: dict[tuple[int, tuple[int, ...], int], float] = {}
            fit_upper_cache: dict[tuple[int, int, tuple[int, ...]], float] = {}
            lagrangian_upper_cache: dict[tuple[int, int, tuple[int, ...]], float] = {}

            def suffix_upper_bound(start: int, needed: int) -> float:
                if needed <= 0:
                    return 0.0
                available_tops = sorted(
                    (
                        ranked[0]["weighted_lift_pct"]
                        for ranked in weighted_rankings[start:]
                        if ranked
                    ),
                    reverse=True,
                )
                if len(available_tops) < needed:
                    return float("-inf")
                return float(sum(available_tops[:needed]))

            def fit_upper_bound(start: int, needed: int, remaining: tuple[int, ...]) -> float:
                """Inventory-aware relaxation: each remaining rally may reuse the same copies."""

                cache_key = (start, needed, remaining)
                if cache_key in fit_upper_cache:
                    return fit_upper_cache[cache_key]
                if needed <= 0:
                    return 0.0
                best_fitting: list[float] = []
                for rally_index in range(start, len(weighted_rankings)):
                    valid_mask = valid_candidate_mask(rally_index, remaining)
                    if valid_mask:
                        best_rank = (valid_mask & -valid_mask).bit_length() - 1
                        best_fitting.append(
                            float(weighted_rankings[rally_index][best_rank]["weighted_lift_pct"])
                        )
                best_fitting.sort(reverse=True)
                result = (
                    float(sum(best_fitting[:needed]))
                    if len(best_fitting) >= needed
                    else float("-inf")
                )
                fit_upper_cache[cache_key] = result
                return result

            price_scale = max(
                (
                    abs(float(ranked[0]["weighted_lift_pct"]))
                    for ranked in weighted_rankings
                    if ranked
                ),
                default=1.0,
            ) / 20.0
            prices = [0.0] * len(ordered_ids)
            best_prices = tuple(prices)
            best_dual = float("inf")
            for iteration in range(80):
                relaxed_choices: list[tuple[float, tuple[int, ...]]] = []
                for ranked in weighted_rankings:
                    best_adjusted = float("-inf")
                    best_usage: tuple[int, ...] = ()
                    for candidate in ranked:
                        adjusted = float(candidate["weighted_lift_pct"]) - sum(
                            price * used
                            for price, used in zip(prices, candidate["usage_tuple"])
                        )
                        if adjusted > best_adjusted:
                            best_adjusted = adjusted
                            best_usage = candidate["usage_tuple"]
                    if best_usage:
                        relaxed_choices.append((best_adjusted, best_usage))
                relaxed_choices.sort(key=lambda item: item[0], reverse=True)
                selected_relaxed = relaxed_choices[:target_completions]
                dual = (
                    sum(item[0] for item in selected_relaxed)
                    + sum(price * available for price, available in zip(prices, initial_remaining))
                )
                if dual < best_dual:
                    best_dual = dual
                    best_prices = tuple(prices)
                relaxed_usage = [
                    sum(item[1][hero_index] for item in selected_relaxed)
                    for hero_index in range(len(ordered_ids))
                ]
                step = price_scale / (1.0 + iteration / 15.0)
                prices = [
                    max(0.0, price + step * (used - available))
                    for price, used, available in zip(prices, relaxed_usage, initial_remaining)
                ]

            adjusted_values: list[list[float]] = []
            adjusted_orders: list[list[int]] = []
            for ranked in weighted_rankings:
                values = [
                    float(candidate["weighted_lift_pct"]) - sum(
                        price * used
                        for price, used in zip(best_prices, candidate["usage_tuple"])
                    )
                    for candidate in ranked
                ]
                adjusted_values.append(values)
                adjusted_orders.append(sorted(range(len(ranked)), key=lambda rank: -values[rank]))

            def lagrangian_upper_bound(
                start: int,
                needed: int,
                remaining: tuple[int, ...],
            ) -> float:
                cache_key = (start, needed, remaining)
                if cache_key in lagrangian_upper_cache:
                    return lagrangian_upper_cache[cache_key]
                if needed <= 0:
                    return 0.0
                relaxed_best: list[float] = []
                for rally_index in range(start, len(weighted_rankings)):
                    valid_mask = valid_candidate_mask(rally_index, remaining)
                    if not valid_mask:
                        continue
                    for rank in adjusted_orders[rally_index]:
                        if valid_mask & (1 << rank):
                            relaxed_best.append(adjusted_values[rally_index][rank])
                            break
                relaxed_best.sort(reverse=True)
                result = (
                    sum(relaxed_best[:needed])
                    + sum(price * available for price, available in zip(best_prices, remaining))
                    + 1e-9
                    if len(relaxed_best) >= needed
                    else float("-inf")
                )
                lagrangian_upper_cache[cache_key] = result
                return result

            def relaxed_upper_bound(start: int, needed: int, remaining: tuple[int, ...]) -> float:
                return min(
                    fit_upper_bound(start, needed, remaining),
                    lagrangian_upper_bound(start, needed, remaining),
                )

            def seed_feasible(
                rally_index: int,
                remaining: tuple[int, ...],
                completed: int,
                choices: tuple[Optional[int], ...],
            ) -> Optional[tuple[Optional[int], ...]]:
                needed = target_completions - completed
                rallies_left = len(normalized_rallies) - rally_index
                if needed == 0:
                    return choices + (None,) * rallies_left
                if needed < 0 or needed > rallies_left or rally_index >= len(normalized_rallies):
                    return None
                valid_mask = valid_candidate_mask(rally_index, remaining)
                while valid_mask:
                    rank_bit = valid_mask & -valid_mask
                    rank = rank_bit.bit_length() - 1
                    valid_mask ^= rank_bit
                    candidate = weighted_rankings[rally_index][rank]
                    usage = candidate["usage_tuple"]
                    next_remaining = tuple(
                        available - required for available, required in zip(remaining, usage)
                    )
                    if fit_upper_bound(rally_index + 1, needed - 1, next_remaining) == float("-inf"):
                        continue
                    seeded = seed_feasible(
                        rally_index + 1,
                        next_remaining,
                        completed + 1,
                        choices + (rank,),
                    )
                    if seeded is not None:
                        return seeded
                if rallies_left > needed:
                    return seed_feasible(
                        rally_index + 1,
                        remaining,
                        completed,
                        choices + (None,),
                    )
                return None

            seeded_choices = seed_feasible(0, initial_remaining, 0, ())
            seed_options: list[tuple[Optional[int], ...]] = []
            if seeded_choices is not None:
                seed_options.append(seeded_choices)
            if target_completions == len(normalized_rallies) and len(normalized_rallies) <= 7:
                for rally_order in permutations(range(len(normalized_rallies))):
                    greedy_remaining = initial_remaining
                    greedy_choices: list[Optional[int]] = [None] * len(normalized_rallies)
                    feasible = True
                    for rally_index in rally_order:
                        valid_mask = valid_candidate_mask(rally_index, greedy_remaining)
                        selected_rank = (
                            (valid_mask & -valid_mask).bit_length() - 1
                            if valid_mask
                            else None
                        )
                        if selected_rank is None:
                            feasible = False
                            break
                        greedy_choices[rally_index] = selected_rank
                        usage = weighted_rankings[rally_index][selected_rank]["usage_tuple"]
                        greedy_remaining = tuple(
                            available - required
                            for available, required in zip(greedy_remaining, usage)
                        )
                    if feasible:
                        seed_options.append(tuple(greedy_choices))

            for seeded_choices in seed_options:
                seeded_weighted = 0.0
                seeded_raw = 0.0
                seeded_completed = 0
                seeded_signature: tuple[int, ...] = ()
                for rally_index, rank in enumerate(seeded_choices):
                    if rank is None:
                        seeded_signature += (0, 0)
                        continue
                    candidate = weighted_rankings[rally_index][rank]
                    seeded_completed += 1
                    seeded_weighted += float(candidate["weighted_lift_pct"])
                    seeded_raw += float(candidate["expected_lift_pct"])
                    seeded_signature += (1, -rank)
                proposed_seed = {
                    "completed": seeded_completed,
                    "weighted_score": seeded_weighted,
                    "raw_score": seeded_raw,
                    "choices": seeded_choices,
                    "tie_signature": seeded_signature,
                }
                if _plan_state_is_better(proposed_seed, incumbent):
                    incumbent = proposed_seed

            def search(
                rally_index: int,
                remaining: tuple[int, ...],
                completed: int,
                weighted_score: float,
                raw_score: float,
                choices: tuple[Optional[int], ...],
                tie_signature: tuple[int, ...],
            ) -> None:
                nonlocal incumbent, search_nodes
                search_nodes += 1
                needed = target_completions - completed
                rallies_left = len(normalized_rallies) - rally_index
                if needed < 0 or needed > rallies_left:
                    return
                if needed == 0:
                    proposed = {
                        "completed": completed,
                        "weighted_score": weighted_score,
                        "raw_score": raw_score,
                        "choices": choices + (None,) * rallies_left,
                        "tie_signature": tie_signature + (0, 0) * rallies_left,
                    }
                    if _plan_state_is_better(proposed, incumbent):
                        incumbent = proposed
                    return
                if rally_index >= len(normalized_rallies):
                    return
                optimistic = weighted_score + relaxed_upper_bound(rally_index, needed, remaining)
                if incumbent is not None and optimistic <= float(incumbent["weighted_score"]) + EPSILON:
                    return
                memo_key = (rally_index, remaining, completed)
                previous_score = seen_scores.get(memo_key)
                if previous_score is not None and weighted_score <= previous_score + EPSILON:
                    return
                seen_scores[memo_key] = weighted_score

                ranked = weighted_rankings[rally_index]
                valid_mask = valid_candidate_mask(rally_index, remaining)
                absolute_remaining_upper = suffix_upper_bound(rally_index + 1, needed - 1)
                while valid_mask:
                    rank_bit = valid_mask & -valid_mask
                    rank = rank_bit.bit_length() - 1
                    valid_mask ^= rank_bit
                    candidate = ranked[rank]
                    absolute_branch_upper = (
                        weighted_score
                        + candidate["weighted_lift_pct"]
                        + absolute_remaining_upper
                    )
                    if (
                        incumbent is not None
                        and absolute_branch_upper <= float(incumbent["weighted_score"]) + EPSILON
                    ):
                        break
                    usage = candidate["usage_tuple"]
                    next_remaining = tuple(
                        available - required for available, required in zip(remaining, usage)
                    )
                    branch_upper = (
                        weighted_score
                        + candidate["weighted_lift_pct"]
                        + relaxed_upper_bound(rally_index + 1, needed - 1, next_remaining)
                    )
                    if incumbent is not None and branch_upper <= float(incumbent["weighted_score"]) + EPSILON:
                        continue
                    search(
                        rally_index + 1,
                        next_remaining,
                        completed + 1,
                        weighted_score + float(candidate["weighted_lift_pct"]),
                        raw_score + float(candidate["expected_lift_pct"]),
                        choices + (rank,),
                        tie_signature + (1, -rank),
                    )

                if rallies_left > needed:
                    search(
                        rally_index + 1,
                        remaining,
                        completed,
                        weighted_score,
                        raw_score,
                        choices + (None,),
                        tie_signature + (0, 0),
                    )

            search(0, initial_remaining, 0, 0.0, 0.0, (), ())
            if incumbent is not None:
                winner_state = incumbent
                break

        if winner_state is None:
            raise ValueError("No feasible rally allocation could be constructed.")
        winner_counts = dict(counts)
        for rally_index, rank in enumerate(winner_state["choices"]):
            if rank is None:
                continue
            for hero_id in rankings[rally_index][rank]["hero_ids"]:
                winner_counts[hero_id] -= 1
        winner_remaining = tuple(winner_counts[hero_id] for hero_id in ordered_ids)

        selected_usage = Counter()
        for rally_index, rank in enumerate(winner_state["choices"]):
            if rank is not None:
                selected_usage.update(rankings[rally_index][rank]["hero_ids"])

        results: list[dict[str, Any]] = []
        for rally_index, rally in enumerate(normalized_rallies):
            selected_rank = winner_state["choices"][rally_index]
            if selected_rank is None:
                available_for_rally = sum(
                    count
                    for hero_id, count in zip(ordered_ids, winner_remaining)
                    if bool(rally.get("include_disputed_skills"))
                    or not bool(get_hero(hero_id).primary_skill().experimental)
                )
                results.append({
                    "rallyId": rally["rally_id"],
                    "complete": False,
                    "recommendedJoiners": [],
                    "evaluation": None,
                    "expectedGoalLiftPct": None,
                    "evaluatedCombinations": len(rankings[rally_index]),
                    "alternatives": [],
                    "warnings": [
                        f"Incomplete rally: shared inventory cannot supply exactly four eligible joiners "
                        f"after the globally optimal {winner_state['completed']}-rally allocation "
                        f"({available_for_rally} eligible copies remain)."
                    ],
                })
                continue

            selected = rankings[rally_index][selected_rank]
            evaluation_kwargs = {
                key: value
                for key, value in rally.items()
                if key not in {"rally_id", "priority_weight"}
            }
            evaluation = self.evaluate(
                joiner_hero_ids=selected["hero_ids"],
                **evaluation_kwargs,
            )
            selected_assessment = evaluation["goalAssessment"]
            joiner_rows = evaluation["joinerSkills"]
            recommended = [
                {
                    "slot": slot,
                    "heroId": row["heroId"],
                    "heroName": row["heroName"],
                    "skillName": row["skillName"],
                    "skillLevel": row["skillLevel"],
                    "experimental": row["experimental"],
                }
                for slot, row in enumerate(joiner_rows, 1)
            ]

            other_usage = selected_usage - Counter(selected["hero_ids"])
            replacement_capacity = {
                hero_id: counts[hero_id] - int(other_usage.get(hero_id, 0))
                for hero_id in ordered_ids
            }
            alternatives = []
            for alternative in rankings[rally_index]:
                if alternative is selected:
                    continue
                if any(
                    int(alternative["usage"].get(hero_id, 0)) > replacement_capacity[hero_id]
                    for hero_id in ordered_ids
                ):
                    continue
                alternative_evaluation = self.evaluate(
                    joiner_hero_ids=alternative["hero_ids"],
                    **evaluation_kwargs,
                )
                alternative_assessment = alternative_evaluation["goalAssessment"]
                alternatives.append({
                    "heroIds": list(alternative["hero_ids"]),
                    "joiners": [get_hero(hero_id).name for hero_id in alternative["hero_ids"]],
                    "expectedGoalLiftPct": alternative["expected_lift_pct"],
                    "floorGoalLiftPct": float(alternative_assessment["floorLiftPct"]),
                    "ceilingGoalLiftPct": float(alternative_assessment["ceilingLiftPct"]),
                })
                if len(alternatives) >= alternative_count:
                    break
            results.append({
                "rallyId": rally["rally_id"],
                "complete": True,
                "recommendedJoiners": recommended,
                "evaluation": evaluation,
                "expectedGoalLiftPct": selected["expected_lift_pct"],
                "floorGoalLiftPct": float(selected_assessment["floorLiftPct"]),
                "ceilingGoalLiftPct": float(selected_assessment["ceilingLiftPct"]),
                "evaluatedCombinations": len(rankings[rally_index]),
                "alternatives": alternatives,
                "warnings": [],
            })

        return {
            "optimizationKind": "GLOBAL_INVENTORY_COMPLETE_9_PLUS_4_EXPECTED_GOAL_LIFT",
            "rankingScenario": "expected",
            "rankingPolicy": (
                "Maximize structurally complete rallies first, then the summed priority-weighted expected "
                "normalized goal lift from all 9 leader skills, leader widgets, and exactly 4 joiner skills."
            ),
            "completedRallies": int(winner_state["completed"]),
            "requestedRallies": len(normalized_rallies),
            "totalExpectedGoalLiftPct": float(winner_state["raw_score"]),
            "weightedExpectedGoalLiftPct": float(winner_state["weighted_score"]),
            "searchNodes": search_nodes,
            "availableHeroCounts": counts,
            "remainingHeroCounts": {
                hero_id: int(count)
                for hero_id, count in zip(ordered_ids, winner_remaining)
            },
            "rallies": sorted(results, key=lambda item: input_rally_order[item["rallyId"]]),
        }
