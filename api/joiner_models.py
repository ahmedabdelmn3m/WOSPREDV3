"""Pydantic request models for rally joiner recommendations."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core_engine.joiner_recommendation import CombatBuffs, CombatStats


def _to_camel(value: str) -> str:
    return re.sub(r"_([a-z])", lambda match: match.group(1).upper(), value)


class JoinerAPIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class CombatStatsInput(JoinerAPIModel):
    attack: float = Field(default=100.0, ge=0)
    defense: float = Field(default=100.0, ge=0)
    health: float = Field(default=100.0, ge=0)
    lethality: float = Field(default=100.0, ge=0)

    def to_domain(self) -> CombatStats:
        return CombatStats(**self.model_dump())


class CombatBuffsInput(JoinerAPIModel):
    attack: float = Field(default=0.0, ge=0)
    defense: float = Field(default=0.0, ge=0)
    health: float = Field(default=0.0, ge=0)
    lethality: float = Field(default=0.0, ge=0)
    damage_dealt: float = Field(default=0.0, ge=0)
    damage_taken_reduction: float = Field(default=0.0, ge=0, lt=1)

    def to_domain(self) -> CombatBuffs:
        return CombatBuffs(**self.model_dump())


class JoinerRecommendationRequest(JoinerAPIModel):
    objective: Literal[
        "MAX_DAMAGE",
        "MAX_DEFENSE",
        "BALANCED",
        "KILL_INFANTRY",
        "KILL_LANCERS",
        "KILL_MARKSMEN",
        "GARRISON_HOLD",
        "GARRISON_BALANCED",
        "COUNTER_BREAK",
    ] = "MAX_DAMAGE"
    joiner_count: int = Field(default=4, ge=1, le=4)
    allow_duplicate_heroes: bool = True
    troop_type: Literal["infantry", "lancer", "marksman"] = "infantry"
    enemy_troop_type: Optional[Literal["infantry", "lancer", "marksman"]] = None
    base_stats: CombatStatsInput = Field(default_factory=CombatStatsInput)
    current_buffs: CombatBuffsInput = Field(default_factory=CombatBuffsInput)
    enemy_stats: Optional[CombatStatsInput] = None
    available_hero_ids: list[str] = Field(default_factory=list)
    available_hero_counts: Optional[dict[str, int]] = None
    excluded_hero_ids: list[str] = Field(default_factory=list)
    minimum_skill_level: Optional[int] = Field(default=5, ge=1, le=5)
    conditional_evaluation: Literal["GUARANTEED", "EXPECTED_VALUE", "EXCLUDED"] = "EXCLUDED"
    activation_probabilities: dict[str, float] = Field(default_factory=dict)
    attack_weight: Optional[float] = Field(default=None, ge=0, le=1)
    defense_weight: Optional[float] = Field(default=None, ge=0, le=1)
    alternative_count: int = Field(default=3, ge=0, le=10)
    troop_split: Optional[dict[str, float]] = None
    include_experimental_skills: bool = False

    @field_validator("available_hero_counts")
    @classmethod
    def counts_cannot_be_negative(cls, value: Optional[dict[str, int]]) -> Optional[dict[str, int]]:
        if value is not None and any(count < 0 for count in value.values()):
            raise ValueError("Available hero counts cannot be negative.")
        return value

    @field_validator("activation_probabilities")
    @classmethod
    def probabilities_are_valid(cls, value: dict[str, float]) -> dict[str, float]:
        invalid = [key for key, probability in value.items() if probability < 0 or probability > 1]
        if invalid:
            raise ValueError("Activation probabilities must be between 0 and 1.")
        return value

    @field_validator("troop_split")
    @classmethod
    def troop_split_is_valid(cls, value: Optional[dict[str, float]]) -> Optional[dict[str, float]]:
        if value is None:
            return value
        unknown = set(value) - {"infantry", "lancer", "marksman"}
        if unknown:
            raise ValueError("Troop split may contain only infantry, lancer, and marksman.")
        if any(amount < 0 for amount in value.values()) or sum(value.values()) <= 0:
            raise ValueError("Troop split values must be non-negative with a positive total.")
        return value

    @model_validator(mode="after")
    def balanced_weights_sum_to_one(self) -> "JoinerRecommendationRequest":
        if (
            self.attack_weight is not None
            and self.defense_weight is not None
            and abs((self.attack_weight + self.defense_weight) - 1.0) > 1e-9
        ):
            raise ValueError("Attack and defense weights must sum to 1.")
        return self

    def to_service_kwargs(self) -> dict:
        return {
            "objective": self.objective,
            "joiner_count": self.joiner_count,
            "allow_duplicate_heroes": self.allow_duplicate_heroes,
            "troop_type": self.troop_type,
            "enemy_troop_type": self.enemy_troop_type,
            "base_stats": self.base_stats.to_domain(),
            "current_buffs": self.current_buffs.to_domain(),
            "enemy_stats": self.enemy_stats.to_domain() if self.enemy_stats else None,
            "available_hero_ids": self.available_hero_ids,
            "available_hero_counts": self.available_hero_counts,
            "excluded_hero_ids": self.excluded_hero_ids,
            "minimum_skill_level": self.minimum_skill_level,
            "conditional_evaluation": self.conditional_evaluation,
            "activation_probabilities": self.activation_probabilities,
            "attack_weight": self.attack_weight,
            "defense_weight": self.defense_weight,
            "alternative_count": self.alternative_count,
            "troop_split": self.troop_split,
            "include_experimental_skills": self.include_experimental_skills,
        }
