"""Pure rally-joiner recommendation and comparison engine.

This module ranks configured level-5 primary expedition skills. It is a
transparent comparison model, not a claim about Whiteout Survival's hidden
combat implementation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations, combinations_with_replacement
from math import prod
from typing import Any, Iterable, Mapping, Optional, Sequence

from hero_data import HEROES_BY_ID, Hero


OBJECTIVES = ("MAX_DAMAGE", "MAX_DEFENSE", "BALANCED")
STACKING_METHODS = (
    "ADDITIVE",
    "MULTIPLICATIVE",
    "HIGHEST_ONLY",
    "LOWEST_ONLY",
    "UNIQUE",
    "CAPPED_ADDITIVE",
    "CONDITIONAL",
)
CONDITIONAL_MODES = ("GUARANTEED", "EXPECTED_VALUE", "EXCLUDED")
TROOP_TYPES = ("infantry", "lancer", "marksman")
EFFECT_FIELDS = (
    "attack_bonus",
    "defense_bonus",
    "health_bonus",
    "lethality_bonus",
    "damage_dealt_bonus",
    "damage_taken_reduction",
    "enemy_damage_taken_increase",
    "enemy_attack_reduction",
    "enemy_defense_reduction",
    "enemy_health_reduction",
    "enemy_lethality_reduction",
)
COUNTERS = {
    "infantry": "lancer",
    "lancer": "marksman",
    "marksman": "infantry",
}
EPSILON = 1e-12


@dataclass(frozen=True)
class HeroJoinerEffect:
    hero_id: str
    hero_name: str
    skill_name: str
    skill_level: int = 5
    generation: Optional[int] = None
    hero_class: str = "unknown"
    troop_type: str = "unknown"
    applicable_as_joiner: bool = True
    applicable_as_rally_leader: bool = True
    attack_bonus: float = 0.0
    defense_bonus: float = 0.0
    health_bonus: float = 0.0
    lethality_bonus: float = 0.0
    damage_dealt_bonus: float = 0.0
    damage_taken_reduction: float = 0.0
    enemy_damage_taken_increase: float = 0.0
    enemy_attack_reduction: float = 0.0
    enemy_defense_reduction: float = 0.0
    enemy_health_reduction: float = 0.0
    enemy_lethality_reduction: float = 0.0
    activation_condition: Optional[str] = None
    activation_probability: Optional[float] = None
    target_troop_type: str = "all_troops"
    max_stacks: int = 4
    stack_group: str = ""
    stacking_method: str = "ADDITIVE"
    priority_order: int = 0
    source: str = "unknown"
    confidence: str = "low"
    notes: str = ""

    def effect_values(self) -> dict[str, float]:
        return {name: float(getattr(self, name)) for name in EFFECT_FIELDS}


@dataclass(frozen=True)
class CombatStats:
    attack: float = 100.0
    defense: float = 100.0
    health: float = 100.0
    lethality: float = 100.0


@dataclass(frozen=True)
class CombatBuffs:
    attack: float = 0.0
    defense: float = 0.0
    health: float = 0.0
    lethality: float = 0.0
    damage_dealt: float = 0.0
    damage_taken_reduction: float = 0.0


@dataclass
class StackedEffects:
    totals: dict[str, float] = field(default_factory=lambda: {name: 0.0 for name in EFFECT_FIELDS})
    explanations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    conditional_count: int = 0


class HeroJoinerRepository:
    """Adapts the existing structured hero data into joiner-only effects."""

    EFFECT_MAP = {
        "attack_up": "attack_bonus",
        "defense_up": "defense_bonus",
        "health_up": "health_bonus",
        "lethality_up": "lethality_bonus",
        "damage_up": "damage_dealt_bonus",
        "attack_damage_up": "damage_dealt_bonus",
        "damage_taken_down": "damage_taken_reduction",
        "enemy_damage_taken_up": "enemy_damage_taken_increase",
        "enemy_attack_down": "enemy_attack_reduction",
        "enemy_defense_down": "enemy_defense_reduction",
        "enemy_health_down": "enemy_health_reduction",
        "enemy_lethality_down": "enemy_lethality_reduction",
    }

    def __init__(self, heroes: Optional[Mapping[str, Hero]] = None):
        self._heroes = heroes or HEROES_BY_ID

    def list_joiner_effects(self) -> list[HeroJoinerEffect]:
        effects: list[HeroJoinerEffect] = []
        for hero in sorted(self._heroes.values(), key=lambda item: (item.name.lower(), item.id)):
            primary = hero.primary_skill()
            if not primary or not getattr(primary, "applicable_as_joiner", True):
                continue
            effect_field = self.EFFECT_MAP.get(primary.effect_type)
            if not effect_field:
                continue
            values = {name: 0.0 for name in EFFECT_FIELDS}
            values[effect_field] = primary.value_decimal
            effects.append(HeroJoinerEffect(
                hero_id=hero.id,
                hero_name=hero.name,
                generation=hero.generation,
                hero_class=hero.hero_type,
                troop_type=hero.hero_type,
                skill_name=primary.name,
                skill_level=getattr(primary, "skill_level", 5),
                applicable_as_joiner=True,
                applicable_as_rally_leader=getattr(primary, "applicable_as_rally_leader", True),
                activation_condition=getattr(primary, "activation_condition", None),
                activation_probability=getattr(primary, "activation_probability", None),
                target_troop_type=primary.target_scope,
                max_stacks=max(1, int(getattr(primary, "max_stacks", 4))),
                stack_group=getattr(primary, "stack_group", "") or effect_field,
                stacking_method=str(getattr(primary, "stacking_method", "ADDITIVE")).upper(),
                priority_order=int(getattr(primary, "priority_order", 0)),
                source=primary.source,
                confidence=primary.confidence,
                notes=primary.notes,
                **values,
            ))
        return effects


def calculate_effective_attack(base_attack: float, total_attack_bonus: float) -> float:
    return float(base_attack) * (1.0 + float(total_attack_bonus))


def calculate_effective_lethality(base_lethality: float, total_lethality_bonus: float) -> float:
    return float(base_lethality) * (1.0 + float(total_lethality_bonus))


def calculate_effective_defense(base_defense: float, total_defense_bonus: float) -> float:
    return float(base_defense) * (1.0 + float(total_defense_bonus))


def calculate_effective_health(base_health: float, total_health_bonus: float) -> float:
    return float(base_health) * (1.0 + float(total_health_bonus))


def calculate_counter_multiplier(attacking_troop: str, target_troop: Optional[str]) -> float:
    attacker = str(attacking_troop or "").lower()
    target = str(target_troop or "").lower()
    return 1.10 if COUNTERS.get(attacker) == target else 1.00


def calculate_damage_score(
    base_stats: CombatStats,
    buffs: CombatBuffs,
    effects: Optional[Mapping[str, float]] = None,
    troop_type: str = "infantry",
    enemy_troop_type: Optional[str] = None,
    enemy_stats: Optional[CombatStats] = None,
) -> dict[str, Optional[float]]:
    totals = _effect_totals(effects)
    effective_attack = calculate_effective_attack(base_stats.attack, buffs.attack + totals["attack_bonus"])
    effective_lethality = calculate_effective_lethality(base_stats.lethality, buffs.lethality + totals["lethality_bonus"])
    base_damage = (effective_attack * effective_lethality) / 100.0
    counter_multiplier = calculate_counter_multiplier(troop_type, enemy_troop_type)
    damage_multiplier = 1.0 + buffs.damage_dealt + totals["damage_dealt_bonus"]
    enemy_damage_multiplier = 1.0 + totals["enemy_damage_taken_increase"]
    raw_score = base_damage * counter_multiplier * damage_multiplier * enemy_damage_multiplier
    penetration = None
    enemy_reduction_multiplier = 1.0
    if enemy_stats is not None:
        adjusted_enemy_defense = max(0.0, enemy_stats.defense * (1.0 - totals["enemy_defense_reduction"]))
        adjusted_enemy_health = max(0.0, enemy_stats.health * (1.0 - totals["enemy_health_reduction"]))
        own_attack_pct = (buffs.attack + totals["attack_bonus"]) * 100.0
        own_lethality_pct = (buffs.lethality + totals["lethality_bonus"]) * 100.0
        penetration = (
            (100.0 + own_attack_pct) / max(EPSILON, 100.0 + adjusted_enemy_defense)
        ) * (
            (100.0 + own_lethality_pct) / max(EPSILON, 100.0 + adjusted_enemy_health)
        )
        enemy_reduction_multiplier = (
            (100.0 + enemy_stats.defense) / max(EPSILON, 100.0 + adjusted_enemy_defense)
        ) * (
            (100.0 + enemy_stats.health) / max(EPSILON, 100.0 + adjusted_enemy_health)
        )
    return {
        "score": raw_score * enemy_reduction_multiplier,
        "raw_score": raw_score,
        "effective_attack": effective_attack,
        "effective_lethality": effective_lethality,
        "counter_multiplier": counter_multiplier,
        "damage_multiplier": damage_multiplier,
        "enemy_damage_multiplier": enemy_damage_multiplier,
        "penetration_score": penetration,
    }


def calculate_defense_score(
    base_stats: CombatStats,
    buffs: CombatBuffs,
    effects: Optional[Mapping[str, float]] = None,
    enemy_stats: Optional[CombatStats] = None,
) -> dict[str, Optional[float]]:
    totals = _effect_totals(effects)
    reduction = buffs.damage_taken_reduction + totals["damage_taken_reduction"]
    if reduction >= 1.0:
        raise ValueError("Damage-taken reduction cannot reach or exceed 100%.")
    effective_defense = calculate_effective_defense(base_stats.defense, buffs.defense + totals["defense_bonus"])
    effective_health = calculate_effective_health(base_stats.health, buffs.health + totals["health_bonus"])
    base_score = (effective_defense * effective_health) / 100.0
    adjusted_score = base_score / max(EPSILON, 1.0 - reduction)
    incoming_pressure = None
    enemy_reduction_multiplier = 1.0
    if enemy_stats is not None:
        adjusted_enemy_attack = max(0.0, enemy_stats.attack * (1.0 - totals["enemy_attack_reduction"]))
        adjusted_enemy_lethality = max(0.0, enemy_stats.lethality * (1.0 - totals["enemy_lethality_reduction"]))
        own_defense_pct = (buffs.defense + totals["defense_bonus"]) * 100.0
        own_health_pct = (buffs.health + totals["health_bonus"]) * 100.0
        incoming_pressure = (
            (100.0 + adjusted_enemy_attack) / max(EPSILON, 100.0 + own_defense_pct)
        ) * (
            (100.0 + adjusted_enemy_lethality) / max(EPSILON, 100.0 + own_health_pct)
        )
        enemy_reduction_multiplier = (
            (100.0 + enemy_stats.attack) / max(EPSILON, 100.0 + adjusted_enemy_attack)
        ) * (
            (100.0 + enemy_stats.lethality) / max(EPSILON, 100.0 + adjusted_enemy_lethality)
        )
    return {
        "score": adjusted_score * enemy_reduction_multiplier,
        "base_score": base_score,
        "adjusted_score": adjusted_score,
        "effective_defense": effective_defense,
        "effective_health": effective_health,
        "incoming_pressure": incoming_pressure,
        "incoming_damage_multiplier": 1.0 - reduction,
    }


def calculate_balanced_score(
    damage_ratio: float,
    defense_ratio: float,
    attack_weight: float = 0.5,
    defense_weight: float = 0.5,
) -> float:
    if abs((attack_weight + defense_weight) - 1.0) > 1e-9:
        raise ValueError("Attack and defense weights must sum to 1.")
    return max(0.0, damage_ratio) ** attack_weight * max(0.0, defense_ratio) ** defense_weight


def _effect_totals(effects: Optional[Mapping[str, float]]) -> dict[str, float]:
    source = effects or {}
    return {name: float(source.get(name, 0.0)) for name in EFFECT_FIELDS}


def _effect_applies(effect: HeroJoinerEffect, troop_type: str) -> bool:
    target = str(effect.target_troop_type or "all_troops").lower()
    return target in {"all", "all_troops", str(troop_type).lower()}


def _conditional_factor(
    effect: HeroJoinerEffect,
    conditional_mode: str,
    activation_probabilities: Mapping[str, float],
    result: StackedEffects,
) -> Optional[float]:
    conditional = bool(effect.activation_condition) or effect.stacking_method == "CONDITIONAL"
    if not conditional:
        return 1.0
    result.conditional_count += 1
    mode = conditional_mode.upper()
    if mode == "GUARANTEED":
        return 1.0
    if mode == "EXCLUDED":
        result.warnings.append(f"{effect.hero_name}: conditional skill excluded from scoring.")
        return None
    probability = activation_probabilities.get(effect.hero_id)
    if probability is None:
        probability = activation_probabilities.get(effect.stack_group)
    if probability is None:
        probability = effect.activation_probability
    if probability is None:
        result.warnings.append(f"{effect.hero_name}: activation probability is missing; conditional effect excluded.")
        return None
    if probability < 0.0 or probability > 1.0:
        raise ValueError(f"Activation probability for {effect.hero_name} must be between 0 and 1.")
    return float(probability)


def stack_hero_effects(
    effects: Sequence[HeroJoinerEffect],
    troop_type: str,
    conditional_mode: str = "EXCLUDED",
    activation_probabilities: Optional[Mapping[str, float]] = None,
) -> StackedEffects:
    if conditional_mode.upper() not in CONDITIONAL_MODES:
        raise ValueError(f"Unsupported conditional evaluation mode: {conditional_mode}.")
    result = StackedEffects()
    grouped: dict[tuple[str, str], list[tuple[HeroJoinerEffect, float]]] = defaultdict(list)
    probabilities = activation_probabilities or {}
    for effect in effects:
        if not effect.applicable_as_joiner:
            result.ignored.append(f"{effect.hero_name}: skill is not applicable as a rally joiner.")
            continue
        if effect.stacking_method not in STACKING_METHODS:
            raise ValueError(f"The skill's stacking method is not configured for {effect.hero_name}.")
        if not _effect_applies(effect, troop_type):
            result.ignored.append(f"{effect.hero_name}: skill targets {effect.target_troop_type}, not {troop_type}.")
            continue
        factor = _conditional_factor(effect, conditional_mode, probabilities, result)
        if factor is None:
            continue
        for field_name, value in effect.effect_values().items():
            if value == 0:
                continue
            group = effect.stack_group or field_name
            grouped[(field_name, group)].append((effect, value * factor))

    additive_by_field: dict[str, float] = defaultdict(float)
    multiplier_by_field: dict[str, float] = defaultdict(lambda: 1.0)
    for (field_name, group), entries in sorted(grouped.items()):
        methods = {entry[0].stacking_method for entry in entries}
        if len(methods) != 1:
            raise ValueError(f"Stack group '{group}' mixes incompatible stacking methods.")
        method = next(iter(methods))
        ordered = sorted(entries, key=lambda item: (-item[0].priority_order, item[0].hero_name.lower(), item[0].hero_id))
        max_stacks = min(max(1, entry[0].max_stacks) for entry in ordered)
        kept = ordered[:max_stacks]
        if len(ordered) > len(kept):
            result.explanations.append(f"{group}: capped at {max_stacks} stack(s); {len(ordered) - len(kept)} ignored.")
        values = [entry[1] for entry in kept]
        if method == "MULTIPLICATIVE":
            combined = prod(1.0 + value for value in values) - 1.0
            multiplier_by_field[field_name] *= 1.0 + combined
        elif method == "HIGHEST_ONLY":
            combined = max(values)
            additive_by_field[field_name] += combined
        elif method == "LOWEST_ONLY":
            combined = min(values)
            additive_by_field[field_name] += combined
        elif method == "UNIQUE":
            combined = values[0]
            additive_by_field[field_name] += combined
            if len(values) > 1:
                result.explanations.append(f"{group}: UNIQUE kept one effect and ignored {len(values) - 1} duplicate(s).")
        else:
            combined = sum(values)
            additive_by_field[field_name] += combined
        hero_names = ", ".join(entry[0].hero_name for entry in kept)
        result.explanations.append(
            f"{group}: {method} combined {hero_names} into {combined * 100:.2f}% {field_name.replace('_', ' ')}."
        )

    for field_name in EFFECT_FIELDS:
        result.totals[field_name] = (
            (1.0 + additive_by_field[field_name]) * multiplier_by_field[field_name] - 1.0
        )
    return result


def validate_combination(
    combination: Sequence[HeroJoinerEffect],
    joiner_count: int,
    allow_duplicate_heroes: bool,
) -> None:
    if len(combination) != joiner_count:
        raise ValueError(f"A valid recommendation requires exactly {joiner_count} joiner selections.")
    counts = Counter(effect.hero_id for effect in combination)
    if not allow_duplicate_heroes and any(count > 1 for count in counts.values()):
        raise ValueError("Duplicate heroes are disabled for this recommendation.")
    for hero_id, count in counts.items():
        limit = min(effect.max_stacks for effect in combination if effect.hero_id == hero_id)
        if count > limit:
            raise ValueError(f"{hero_id} exceeds its maximum stack limit of {limit}.")


def _inventory_combinations(
    effects: Sequence[HeroJoinerEffect],
    joiner_count: int,
    allow_duplicate_heroes: bool,
    available_counts: Mapping[str, int],
) -> list[tuple[HeroJoinerEffect, ...]]:
    generated: list[tuple[HeroJoinerEffect, ...]] = []

    def visit(index: int, remaining: int, selected: list[HeroJoinerEffect]) -> None:
        if remaining == 0:
            generated.append(tuple(selected))
            return
        if index >= len(effects):
            return
        effect = effects[index]
        inventory = max(0, int(available_counts.get(effect.hero_id, 0)))
        limit = min(inventory, effect.max_stacks, remaining)
        if not allow_duplicate_heroes:
            limit = min(limit, 1)
        for count in range(limit, -1, -1):
            visit(index + 1, remaining - count, selected + [effect] * count)

    visit(0, joiner_count, [])
    return generated


def generate_hero_combinations(
    effects: Sequence[HeroJoinerEffect],
    joiner_count: int = 4,
    allow_duplicate_heroes: bool = True,
    available_counts: Optional[Mapping[str, int]] = None,
) -> list[tuple[HeroJoinerEffect, ...]]:
    if joiner_count < 1 or joiner_count > 4:
        raise ValueError("Joiner count must be between 1 and 4.")
    ordered = sorted(effects, key=lambda effect: (effect.hero_name.lower(), effect.hero_id))
    if available_counts is not None:
        raw = _inventory_combinations(ordered, joiner_count, allow_duplicate_heroes, available_counts)
    elif allow_duplicate_heroes:
        raw = list(combinations_with_replacement(ordered, joiner_count))
    else:
        if len(ordered) < joiner_count:
            raise ValueError("At least four eligible hero selections are required when duplicates are disabled.")
        raw = list(combinations(ordered, joiner_count))
    valid: list[tuple[HeroJoinerEffect, ...]] = []
    for combination in raw:
        try:
            validate_combination(combination, joiner_count, allow_duplicate_heroes)
        except ValueError:
            continue
        valid.append(combination)
    return valid


class CombatScoreCalculator:
    def score(
        self,
        effects: Mapping[str, float],
        base_stats: CombatStats,
        current_buffs: CombatBuffs,
        troop_type: str,
        enemy_troop_type: Optional[str],
        enemy_stats: Optional[CombatStats],
        attack_weight: float,
        defense_weight: float,
    ) -> dict[str, Any]:
        before_damage = calculate_damage_score(base_stats, current_buffs, troop_type=troop_type, enemy_troop_type=enemy_troop_type, enemy_stats=enemy_stats)
        after_damage = calculate_damage_score(base_stats, current_buffs, effects, troop_type, enemy_troop_type, enemy_stats)
        before_defense = calculate_defense_score(base_stats, current_buffs, enemy_stats=enemy_stats)
        after_defense = calculate_defense_score(base_stats, current_buffs, effects, enemy_stats)
        damage_ratio = after_damage["score"] / max(EPSILON, before_damage["score"])
        defense_ratio = after_defense["score"] / max(EPSILON, before_defense["score"])
        return {
            "damage_score_before_joiners": before_damage["score"],
            "damage_score_after_joiners": after_damage["score"],
            "damage_improvement_percentage": (damage_ratio - 1.0) * 100.0,
            "defense_score_before_joiners": before_defense["score"],
            "defense_score_after_joiners": after_defense["score"],
            "defense_improvement_percentage": (defense_ratio - 1.0) * 100.0,
            "damage_ratio": damage_ratio,
            "defense_ratio": defense_ratio,
            "balanced_score": calculate_balanced_score(damage_ratio, defense_ratio, attack_weight, defense_weight),
            "counter_multiplier": after_damage["counter_multiplier"],
            "penetration_score_before_joiners": before_damage["penetration_score"],
            "penetration_score_after_joiners": after_damage["penetration_score"],
            "incoming_pressure_before_joiners": before_defense["incoming_pressure"],
            "incoming_pressure_after_joiners": after_defense["incoming_pressure"],
            "raw_damage_score_after_joiners": after_damage["raw_score"],
            "base_defense_score_after_joiners": after_defense["base_score"],
            "incoming_damage_multiplier": after_defense["incoming_damage_multiplier"],
        }


class HeroCombinationGenerator:
    def generate(
        self,
        effects: Sequence[HeroJoinerEffect],
        joiner_count: int,
        allow_duplicate_heroes: bool,
        available_counts: Optional[Mapping[str, int]] = None,
    ) -> list[tuple[HeroJoinerEffect, ...]]:
        return generate_hero_combinations(effects, joiner_count, allow_duplicate_heroes, available_counts)


class BuffStackingService:
    def stack(
        self,
        effects: Sequence[HeroJoinerEffect],
        troop_type: str,
        conditional_mode: str,
        activation_probabilities: Optional[Mapping[str, float]] = None,
    ) -> StackedEffects:
        return stack_hero_effects(effects, troop_type, conditional_mode, activation_probabilities)


class JoinerRecommendationService:
    def __init__(
        self,
        repository: Optional[HeroJoinerRepository] = None,
        stacker: Optional[BuffStackingService] = None,
        calculator: Optional[CombatScoreCalculator] = None,
        generator: Optional[HeroCombinationGenerator] = None,
    ):
        self.repository = repository or HeroJoinerRepository()
        self.stacker = stacker or BuffStackingService()
        self.calculator = calculator or CombatScoreCalculator()
        self.generator = generator or HeroCombinationGenerator()

    def recommend(
        self,
        objective: str,
        joiner_count: int = 4,
        allow_duplicate_heroes: bool = True,
        troop_type: str = "infantry",
        enemy_troop_type: Optional[str] = None,
        base_stats: Optional[CombatStats] = None,
        current_buffs: Optional[CombatBuffs] = None,
        enemy_stats: Optional[CombatStats] = None,
        available_hero_ids: Optional[Sequence[str]] = None,
        available_hero_counts: Optional[Mapping[str, int]] = None,
        excluded_hero_ids: Optional[Sequence[str]] = None,
        minimum_skill_level: Optional[int] = None,
        conditional_evaluation: str = "EXCLUDED",
        activation_probabilities: Optional[Mapping[str, float]] = None,
        attack_weight: float = 0.5,
        defense_weight: float = 0.5,
        alternative_count: int = 3,
    ) -> dict[str, Any]:
        objective = str(objective or "").upper()
        troop_type = str(troop_type or "").lower()
        enemy_troop_type = str(enemy_troop_type).lower() if enemy_troop_type else None
        if objective not in OBJECTIVES:
            raise ValueError(f"Unsupported objective: {objective}.")
        if troop_type not in TROOP_TYPES:
            raise ValueError("The supplied troop type is invalid.")
        if enemy_troop_type and enemy_troop_type not in TROOP_TYPES:
            raise ValueError("The supplied enemy troop type is invalid.")
        if abs((attack_weight + defense_weight) - 1.0) > 1e-9:
            raise ValueError("Attack and defense weights must sum to 1.")
        base_stats = base_stats or CombatStats()
        current_buffs = current_buffs or CombatBuffs()
        if current_buffs.damage_taken_reduction >= 1.0:
            raise ValueError("Damage-taken reduction cannot reach or exceed 100%.")

        effects = self.repository.list_joiner_effects()
        available = {str(hero_id).lower() for hero_id in (available_hero_ids or [])}
        excluded = {str(hero_id).lower() for hero_id in (excluded_hero_ids or [])}
        if available:
            effects = [effect for effect in effects if effect.hero_id in available]
        effects = [effect for effect in effects if effect.hero_id not in excluded]
        if minimum_skill_level is not None:
            effects = [effect for effect in effects if effect.skill_level >= minimum_skill_level]
        if not effects:
            raise ValueError("No eligible joiner heroes were found.")

        normalized_counts = None
        if available_hero_counts is not None:
            normalized_counts = {str(hero_id).lower(): max(0, int(count)) for hero_id, count in available_hero_counts.items()}
        combinations_to_score = self.generator.generate(
            effects,
            joiner_count,
            allow_duplicate_heroes,
            normalized_counts,
        )
        if not combinations_to_score:
            raise ValueError("No valid hero combination can fill the requested joiner slots.")

        ranked: list[dict[str, Any]] = []
        for combination in combinations_to_score:
            stacked = self.stacker.stack(combination, troop_type, conditional_evaluation, activation_probabilities)
            scores = self.calculator.score(
                stacked.totals,
                base_stats,
                current_buffs,
                troop_type,
                enemy_troop_type,
                enemy_stats,
                attack_weight,
                defense_weight,
            )
            primary = {
                "MAX_DAMAGE": scores["damage_score_after_joiners"],
                "MAX_DEFENSE": scores["defense_score_after_joiners"],
                "BALANCED": scores["balanced_score"],
            }[objective]
            ranked.append({
                "combination": combination,
                "stacked": stacked,
                "scores": scores,
                "primary_score": primary,
                "average_skill_level": sum(effect.skill_level for effect in combination) / len(combination),
                "hero_key": tuple(sorted(effect.hero_id for effect in combination)),
            })
        ranked.sort(key=lambda item: (
            -item["primary_score"],
            -item["scores"]["damage_improvement_percentage"],
            -item["scores"]["defense_improvement_percentage"],
            item["stacked"].conditional_count,
            -item["average_skill_level"],
            item["hero_key"],
        ))

        winner = ranked[0]
        response = self._present_result(winner, objective)
        response["evaluatedCombinations"] = len(ranked)
        response["alternatives"] = [self._present_alternative(item) for item in ranked[1:1 + max(0, alternative_count)]]
        if len(ranked) > 1:
            margin = winner["primary_score"] - ranked[1]["primary_score"]
            response["stackingExplanation"].append(
                f"The winner beat the next alternative by {margin:.8f} on the {objective} ranking score."
            )
        if objective == "MAX_DEFENSE" and winner["scores"]["defense_improvement_percentage"] <= EPSILON:
            response["warnings"].append(
                "No configured level-5 primary joiner skill increases Defense, Health, or Damage Taken Reduction; the defense tie was resolved by damage and deterministic tie-breaks."
            )
        response["modelNote"] = (
            "Comparison model using configured level-5 rally-joiner skills; it is not presented as the game's confirmed hidden combat formula."
        )
        return response

    def _present_result(self, item: Mapping[str, Any], objective: str) -> dict[str, Any]:
        combination = item["combination"]
        stacked: StackedEffects = item["stacked"]
        return {
            "objective": objective,
            "recommendedJoiners": [self._present_joiner(slot, effect) for slot, effect in enumerate(combination, 1)],
            "totalEffects": _camel_effects(stacked.totals),
            "scores": _camel_scores(item["scores"]),
            "stackingExplanation": list(stacked.explanations),
            "warnings": list(dict.fromkeys(stacked.warnings + stacked.ignored)),
        }

    def _present_alternative(self, item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "joiners": [effect.hero_name for effect in item["combination"]],
            "heroIds": [effect.hero_id for effect in item["combination"]],
            "totalEffects": _camel_effects(item["stacked"].totals),
            "scores": _camel_scores(item["scores"]),
        }

    @staticmethod
    def _present_joiner(slot: int, effect: HeroJoinerEffect) -> dict[str, Any]:
        return {
            "slot": slot,
            "heroId": effect.hero_id,
            "heroName": effect.hero_name,
            "generation": effect.generation,
            "heroClass": effect.hero_class,
            "troopType": effect.troop_type,
            "skillName": effect.skill_name,
            "skillLevel": effect.skill_level,
            "targetTroopType": effect.target_troop_type,
            "stackingMethod": effect.stacking_method,
            "maxStacks": effect.max_stacks,
            "contribution": _camel_effects(effect.effect_values()),
            "notes": effect.notes,
        }


def rank_combinations(**kwargs: Any) -> dict[str, Any]:
    return JoinerRecommendationService().recommend(**kwargs)


def explain_recommendation(result: Mapping[str, Any]) -> list[str]:
    return list(result.get("stackingExplanation", [])) + list(result.get("warnings", []))


def _camel_effects(values: Mapping[str, float]) -> dict[str, float]:
    aliases = {
        "attack_bonus": "attackBonus",
        "defense_bonus": "defenseBonus",
        "health_bonus": "healthBonus",
        "lethality_bonus": "lethalityBonus",
        "damage_dealt_bonus": "damageDealtBonus",
        "damage_taken_reduction": "damageTakenReduction",
        "enemy_damage_taken_increase": "enemyDamageTakenIncrease",
        "enemy_attack_reduction": "enemyAttackReduction",
        "enemy_defense_reduction": "enemyDefenseReduction",
        "enemy_health_reduction": "enemyHealthReduction",
        "enemy_lethality_reduction": "enemyLethalityReduction",
    }
    return {aliases[name]: float(values.get(name, 0.0)) for name in EFFECT_FIELDS}


def _camel_scores(values: Mapping[str, Any]) -> dict[str, Any]:
    aliases = {
        "damage_score_before_joiners": "damageScoreBeforeJoiners",
        "damage_score_after_joiners": "damageScoreAfterJoiners",
        "damage_improvement_percentage": "damageImprovementPercentage",
        "defense_score_before_joiners": "defenseScoreBeforeJoiners",
        "defense_score_after_joiners": "defenseScoreAfterJoiners",
        "defense_improvement_percentage": "defenseImprovementPercentage",
        "damage_ratio": "damageRatio",
        "defense_ratio": "defenseRatio",
        "balanced_score": "balancedScore",
        "counter_multiplier": "counterMultiplier",
        "penetration_score_before_joiners": "penetrationScoreBeforeJoiners",
        "penetration_score_after_joiners": "penetrationScoreAfterJoiners",
        "incoming_pressure_before_joiners": "incomingPressureBeforeJoiners",
        "incoming_pressure_after_joiners": "incomingPressureAfterJoiners",
        "raw_damage_score_after_joiners": "rawDamageScoreAfterJoiners",
        "base_defense_score_after_joiners": "baseDefenseScoreAfterJoiners",
        "incoming_damage_multiplier": "incomingDamageMultiplier",
    }
    return {aliases[name]: value for name, value in values.items() if name in aliases}
