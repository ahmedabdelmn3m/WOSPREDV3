"""
Structured hero data for rally, joiner, and garrison skill mechanics.

The official Combat FAQ defines which skills are activated in rallies and
garrisons. The actual hero values below are marked by source and confidence;
user-provided values are not presented as official hidden formula data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

TROOP_TYPES = ("infantry", "lancer", "marksman")
EFFECT_TYPES = (
    "attack_up",
    "damage_up",
    "attack_damage_up",
    "lethality_up",
    "defense_up",
    "health_up",
    "damage_taken_down",
    "unknown",
)


@dataclass(frozen=True)
class ExpeditionSkill:
    slot: int
    name: str
    effect_type: str
    value_pct: float
    target_scope: str = "all_troops"
    applies_to: str = "both"
    source: str = "unknown"
    confidence: str = "low"
    notes: str = ""

    @property
    def value_decimal(self) -> float:
        return self.value_pct / 100.0


@dataclass(frozen=True)
class HeroWidget:
    supported: bool = False
    effect_type: Optional[str] = None
    value_pct_by_level: Optional[Dict[str, float]] = None
    target_scope: Optional[str] = None
    notes: str = "Widget values are not verified for this hero."


@dataclass(frozen=True)
class Hero:
    id: str
    name: str
    hero_type: str = "unknown"
    generation: Optional[int] = None
    expedition_skills: List[ExpeditionSkill] = field(default_factory=list)
    widget: HeroWidget = field(default_factory=HeroWidget)

    def primary_skill(self) -> Optional[ExpeditionSkill]:
        if not self.expedition_skills:
            return None
        return sorted(self.expedition_skills, key=lambda skill: skill.slot)[0]


def skill(
    slot: int,
    name: str,
    effect_type: str,
    value_pct: float,
    target_scope: str = "all_troops",
    applies_to: str = "both",
    source: str = "user_provided",
    confidence: str = "medium",
    notes: str = "Assumes 4-star hero with Expedition Skill level 5 primary/top-right skill.",
) -> ExpeditionSkill:
    return ExpeditionSkill(
        slot=slot,
        name=name,
        effect_type=effect_type,
        value_pct=value_pct,
        target_scope=target_scope,
        applies_to=applies_to,
        source=source,
        confidence=confidence,
        notes=notes,
    )


def widget_supported(notes: str = "Widget supported; exact per-level values are pending verification.") -> HeroWidget:
    return HeroWidget(
        supported=True,
        effect_type=None,
        value_pct_by_level=None,
        target_scope=None,
        notes=notes,
    )


HEROES_BY_ID: Dict[str, Hero] = {
    "reina": Hero(
        id="reina",
        name="Reina",
        hero_type="lancer",
        generation=4,
        expedition_skills=[
            skill(1, "Primary Expedition Skill", "attack_damage_up", 30.0, "all_troops"),
        ],
    ),
    "jeronimo": Hero(
        id="jeronimo",
        name="Jeronimo",
        hero_type="infantry",
        generation=1,
        expedition_skills=[
            skill(1, "Primary Expedition Skill", "damage_up", 25.0, "all_troops"),
        ],
        widget=widget_supported(),
    ),
    "jessie": Hero(
        id="jessie",
        name="Jessie",
        hero_type="unknown",
        generation=None,
        expedition_skills=[
            skill(1, "Primary Expedition Skill", "damage_up", 25.0, "all_troops"),
        ],
    ),
    "seo-yoon": Hero(
        id="seo-yoon",
        name="Seo-Yoon",
        hero_type="unknown",
        generation=None,
        expedition_skills=[
            skill(
                1,
                "Primary Expedition Skill",
                "damage_up",
                25.0,
                "all_troops",
                notes="Corrected from old attack_only +50% model based on current user-provided reference.",
            ),
        ],
    ),
    "jasser": Hero(
        id="jasser",
        name="Jasser",
        hero_type="unknown",
        generation=None,
        expedition_skills=[
            skill(1, "Primary Expedition Skill", "damage_up", 25.0, "all_troops"),
        ],
    ),
    "flint": Hero(
        id="flint",
        name="Flint",
        hero_type="infantry",
        generation=2,
        expedition_skills=[
            skill(1, "Primary Expedition Skill", "damage_up", 100.0, "infantry"),
        ],
        widget=widget_supported(),
    ),
    "philly": Hero(
        id="philly",
        name="Philly",
        hero_type="lancer",
        generation=2,
        expedition_skills=[
            skill(1, "Primary Expedition Skill", "attack_up", 15.0, "all_troops"),
        ],
    ),
    # Basic leader-march heroes retained for validation/dropdowns. Skill values
    # are unknown unless explicitly provided above.
    "natalia": Hero("natalia", "Natalia", "infantry", 1, [], widget_supported()),
    "molly": Hero("molly", "Molly", "lancer", 1, []),
    "zinman": Hero("zinman", "Zinman", "marksman", 1, []),
    "alonso": Hero("alonso", "Alonso", "marksman", 2, [], widget_supported()),
    "logan": Hero("logan", "Logan", "infantry", 3, [], widget_supported()),
    "mia": Hero("mia", "Mia", "lancer", 3, [], widget_supported()),
    "greg": Hero("greg", "Greg", "marksman", 3, [], widget_supported()),
    "ahmose": Hero("ahmose", "Ahmose", "infantry", 4, [], widget_supported()),
    "lynn": Hero("lynn", "Lynn", "marksman", 4, [], widget_supported()),
    "hector": Hero("hector", "Hector", "infantry", 5, [], widget_supported()),
    "norah": Hero("norah", "Norah", "lancer", 5, [], widget_supported()),
    "gwen": Hero("gwen", "Gwen", "marksman", 5, [], widget_supported()),
}

# Compatibility lookup for older call-sites/tests that pass display names.
HEROES: Dict[str, Hero] = {hero.name: hero for hero in HEROES_BY_ID.values()}
HEROES.update({hero.id: hero for hero in HEROES_BY_ID.values()})


def normalize_hero_id(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("id") or value.get("name") or ""
    value = str(value or "").strip()
    lower = value.lower().replace("_", "-")
    aliases = {
        "seo yoon": "seo-yoon",
        "seoyoon": "seo-yoon",
        "seo-yoon": "seo-yoon",
    }
    return aliases.get(lower, lower)


def get_hero(value: Any) -> Optional[Hero]:
    if isinstance(value, Hero):
        return value
    hero_id = normalize_hero_id(value)
    if hero_id in HEROES_BY_ID:
        return HEROES_BY_ID[hero_id]
    return HEROES.get(str(value or "").strip())


def hero_to_dict(hero: Hero) -> dict:
    return {
        "id": hero.id,
        "name": hero.name,
        "hero_type": hero.hero_type,
        "generation": hero.generation,
        "expedition_skills": [skill.__dict__ for skill in hero.expedition_skills],
        "widget": {
            "supported": hero.widget.supported,
            "effect_type": hero.widget.effect_type,
            "value_pct_by_level": hero.widget.value_pct_by_level,
            "target_scope": hero.widget.target_scope,
            "notes": hero.widget.notes,
        },
    }
