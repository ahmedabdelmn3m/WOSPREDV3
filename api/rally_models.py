"""Pydantic request models for complete rally evaluations."""

from __future__ import annotations

from collections import Counter
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator

from api.joiner_models import CombatBuffsInput, CombatStatsInput, JoinerAPIModel
from hero_data import HEROES_BY_ID, TROOP_TYPES


RallyObjective = Literal[
    "MAX_DAMAGE",
    "MAX_DEFENSE",
    "BALANCED",
    "KILL_INFANTRY",
    "KILL_LANCERS",
    "KILL_MARKSMEN",
    "GARRISON_HOLD",
    "GARRISON_BALANCED",
    "COUNTER_BREAK",
]
TroopType = Literal["infantry", "lancer", "marksman"]


class LeaderHeroInput(JoinerAPIModel):
    """One of the three Mythic heroes supplied by the rally leader."""

    hero_id: str = Field(min_length=1)
    widget_level: int = Field(default=0, ge=0, le=10)


class RallyLoadoutInput(JoinerAPIModel):
    """The leader, report, and objective inputs shared by full-rally operations."""

    objective: RallyObjective = "MAX_DAMAGE"
    leader_heroes: list[LeaderHeroInput] = Field(min_length=3, max_length=3)
    troop_type: TroopType = "infantry"
    enemy_troop_type: Optional[TroopType] = None
    base_stats: CombatStatsInput = Field(default_factory=CombatStatsInput)
    current_buffs: CombatBuffsInput = Field(default_factory=CombatBuffsInput)
    enemy_stats: Optional[CombatStatsInput] = None
    troop_split: Optional[dict[str, float]] = None
    include_disputed_skills: bool = False

    @field_validator("troop_split")
    @classmethod
    def troop_split_is_valid(cls, value: Optional[dict[str, float]]) -> Optional[dict[str, float]]:
        if value is None:
            return value
        unknown = set(value) - set(TROOP_TYPES)
        if unknown:
            raise ValueError("Troop split may contain only infantry, lancer, and marksman.")
        if any(amount < 0 for amount in value.values()) or sum(value.values()) <= 0:
            raise ValueError("Troop split values must be non-negative with a positive total.")
        return value

    @model_validator(mode="after")
    def leaders_form_complete_mythic_march(self) -> "RallyLoadoutInput":
        hero_ids = [selection.hero_id for selection in self.leader_heroes]
        duplicate_ids = sorted(hero_id for hero_id, count in Counter(hero_ids).items() if count > 1)
        if duplicate_ids:
            raise ValueError(f"Leader hero IDs must be unique: {', '.join(duplicate_ids)}.")

        hero_types: list[str] = []
        for hero_id in hero_ids:
            hero = HEROES_BY_ID.get(hero_id)
            if hero is None:
                raise ValueError(f"Unknown leader hero ID: {hero_id}.")
            if hero.rarity.casefold() != "mythic" or hero.generation not in range(1, 6):
                raise ValueError(f"Leader hero {hero_id} must be a Mythic Generation 1-5 hero.")
            if sorted(skill.slot for skill in hero.expedition_skills) != [1, 2, 3]:
                raise ValueError(f"Leader hero {hero_id} must have exactly 3 Expedition skills.")
            if any(not skill.applicable_as_rally_leader for skill in hero.expedition_skills):
                raise ValueError(f"Leader hero {hero_id} has a skill that is not rally-leader eligible.")
            hero_types.append(hero.hero_type)

        expected_types = Counter(TROOP_TYPES)
        if Counter(hero_types) != expected_types:
            raise ValueError("Leader heroes must include exactly one infantry, one lancer, and one marksman hero.")
        return self

    def to_loadout_kwargs(self) -> dict:
        """Convert shared API inputs to the evaluator's snake_case arguments."""
        return {
            "objective": self.objective,
            "leader_heroes": [selection.model_dump(by_alias=False) for selection in self.leader_heroes],
            "troop_type": self.troop_type,
            "enemy_troop_type": self.enemy_troop_type,
            "base_stats": self.base_stats.to_domain(),
            "current_buffs": self.current_buffs.to_domain(),
            "enemy_stats": self.enemy_stats.to_domain() if self.enemy_stats else None,
            "troop_split": self.troop_split,
            "include_disputed_skills": self.include_disputed_skills,
        }


class RallyEvaluationRequest(RallyLoadoutInput):
    """A complete three-leader/four-joiner rally evaluation request."""

    joiner_hero_ids: list[str] = Field(min_length=4, max_length=4)

    @field_validator("joiner_hero_ids")
    @classmethod
    def joiners_are_modeled(cls, value: list[str]) -> list[str]:
        for hero_id in value:
            hero = HEROES_BY_ID.get(hero_id)
            if hero is None:
                raise ValueError(f"Unknown joiner hero ID: {hero_id}.")
            if hero.primary_skill() is None or not hero.primary_skill().applicable_as_joiner:
                raise ValueError(f"Joiner hero {hero_id} has no primary Expedition skill.")
        return value

    def to_service_kwargs(self) -> dict:
        """Convert API inputs to the rally service's snake_case arguments."""

        return {**self.to_loadout_kwargs(), "joiner_hero_ids": list(self.joiner_hero_ids)}


class RallyPlanItemInput(RallyLoadoutInput):
    """One leader loadout whose four joiner slots are selected by the plan optimizer."""

    rally_id: str = Field(min_length=1)
    priority_weight: float = Field(default=1.0, gt=0)

    def to_service_kwargs(self) -> dict:
        return {
            "rally_id": self.rally_id,
            "priority_weight": self.priority_weight,
            **self.to_loadout_kwargs(),
        }


class RallyPlanOptimizationRequest(JoinerAPIModel):
    """Optimize shared joiner inventory across complete 9+4 rally loadouts."""

    rallies: list[RallyPlanItemInput] = Field(min_length=1, max_length=12)
    available_hero_ids: list[str] = Field(min_length=1)
    available_hero_counts: dict[str, int] = Field(default_factory=dict)
    alternative_count: int = Field(default=2, ge=0, le=5)

    @field_validator("available_hero_ids")
    @classmethod
    def available_joiners_are_modeled_and_unique(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_hero_id in value:
            hero_id = str(raw_hero_id).lower()
            if hero_id in seen:
                raise ValueError(f"Available joiner hero IDs must be unique: {hero_id}.")
            hero = HEROES_BY_ID.get(hero_id)
            if hero is None:
                raise ValueError(f"Unknown joiner hero ID: {hero_id}.")
            if hero.primary_skill() is None or not hero.primary_skill().applicable_as_joiner:
                raise ValueError(f"Joiner hero {hero_id} has no primary Expedition skill.")
            seen.add(hero_id)
            normalized.append(hero_id)
        return normalized

    @field_validator("available_hero_counts")
    @classmethod
    def counts_are_modeled_and_non_negative(cls, value: dict[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for raw_hero_id, count in value.items():
            hero_id = str(raw_hero_id).lower()
            if hero_id not in HEROES_BY_ID:
                raise ValueError(f"Unknown joiner hero ID in availability: {hero_id}.")
            if count < 0:
                raise ValueError("Available hero counts cannot be negative.")
            normalized[hero_id] = int(count)
        return normalized

    def to_service_kwargs(self) -> dict:
        return {
            "rallies": [rally.to_service_kwargs() for rally in self.rallies],
            "available_hero_ids": list(self.available_hero_ids),
            "available_hero_counts": dict(self.available_hero_counts),
            "alternative_count": self.alternative_count,
        }


# Descriptive alias for callers that prefer the endpoint-specific name.
RallyLeaderHeroInput = LeaderHeroInput
