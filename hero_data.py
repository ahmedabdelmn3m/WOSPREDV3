"""
Structured hero data for rally, joiner, and garrison skill mechanics.

The official Combat FAQ defines which skills are activated in rallies and
garrisons. The actual hero values below are marked by source and confidence;
user-provided values are not presented as official hidden formula data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

TROOP_TYPES = ("infantry", "lancer", "marksman")
EFFECT_TYPES = (
    "attack_up",
    "damage_up",
    "attack_damage_up",
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
    "unknown",
)


@dataclass(frozen=True)
class SkillEffectComponent:
    """One independently stacked component of an expedition skill.

    The canonical key deliberately includes the affected side, troop scope,
    and effect type.  Equal keys add; different keys remain separate factors
    in the combat scorer.
    """

    effect_type: str
    value_pct: float
    target_scope: str = "all_troops"
    affected_side: str = "friendly"
    stacking_method: str = "ADDITIVE"
    max_stacks: int = 4

    @property
    def value_decimal(self) -> float:
        return self.value_pct / 100.0

    @property
    def canonical_stack_key(self) -> str:
        return f"{self.affected_side}:{self.target_scope}:{self.effect_type}"


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
    skill_level: int = 5
    applicable_as_joiner: bool = True
    applicable_as_rally_leader: bool = True
    stacking_method: str = "ADDITIVE"
    max_stacks: int = 4
    stack_group: str = ""
    activation_condition: Optional[str] = None
    activation_probability: Optional[float] = None
    priority_order: int = 0
    affected_side: str = "friendly"
    effect_components: Tuple[SkillEffectComponent, ...] = ()
    stacking_evidence_level: str = "UNVERIFIED"
    stacking_evidence_source: str = ""
    stacking_evidence_notes: str = ""
    production_eligible: bool = True
    experimental: bool = False

    @property
    def value_decimal(self) -> float:
        return self.value_pct / 100.0

    def resolved_components(self) -> Tuple[SkillEffectComponent, ...]:
        if self.effect_components:
            return self.effect_components
        return (
            SkillEffectComponent(
                effect_type=self.effect_type,
                value_pct=self.value_pct,
                target_scope=self.target_scope,
                affected_side=self.affected_side,
                stacking_method=self.stacking_method,
                max_stacks=self.max_stacks,
            ),
        )


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
    skill_level: int = 5,
    applicable_as_joiner: bool = True,
    applicable_as_rally_leader: bool = True,
    stacking_method: str = "ADDITIVE",
    max_stacks: int = 4,
    stack_group: str = "",
    activation_condition: Optional[str] = None,
    activation_probability: Optional[float] = None,
    priority_order: int = 0,
    affected_side: str = "friendly",
    effect_components: Optional[List[SkillEffectComponent]] = None,
    stacking_evidence_level: str = "UNVERIFIED",
    stacking_evidence_source: str = "",
    stacking_evidence_notes: str = "",
    production_eligible: bool = True,
    experimental: bool = False,
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
        skill_level=skill_level,
        applicable_as_joiner=applicable_as_joiner,
        applicable_as_rally_leader=applicable_as_rally_leader,
        stacking_method=stacking_method,
        max_stacks=max_stacks,
        stack_group=stack_group,
        activation_condition=activation_condition,
        activation_probability=activation_probability,
        priority_order=priority_order,
        affected_side=affected_side,
        effect_components=tuple(effect_components or ()),
        stacking_evidence_level=stacking_evidence_level,
        stacking_evidence_source=stacking_evidence_source,
        stacking_evidence_notes=stacking_evidence_notes,
        production_eligible=production_eligible,
        experimental=experimental,
    )


def component(
    effect_type: str,
    value_pct: float,
    target_scope: str = "all_troops",
    affected_side: str = "friendly",
    stacking_method: str = "ADDITIVE",
    max_stacks: int = 4,
) -> SkillEffectComponent:
    return SkillEffectComponent(
        effect_type=effect_type,
        value_pct=value_pct,
        target_scope=target_scope,
        affected_side=affected_side,
        stacking_method=stacking_method,
        max_stacks=max_stacks,
    )


def widget_supported(notes: str = "Widget supported; exact per-level values are pending verification.") -> HeroWidget:
    return HeroWidget(
        supported=True,
        effect_type=None,
        value_pct_by_level=None,
        target_scope=None,
        notes=notes,
    )


OFFICIAL_DUPLICATE_STACKING_SOURCE = (
    "https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/"
    "8050-if-the-4-skills-of-the-rally-members-are-the-same-as-the-captain-s-will-the-effects-be-stackable/"
)
COMMUNITY_BUCKET_TEST_SOURCE = (
    "https://gall.dcinside.com/mgallery/board/view/?id=whiteoutsv&no=79968"
)
COMMUNITY_DEFENSE_MODEL_SOURCE = (
    "https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/8052-about-skill-descriptions/"
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
        hero_type="lancer",
        generation=None,
        expedition_skills=[
            skill(
                1,
                "Stand of Arms",
                "damage_up",
                25.0,
                "all_troops",
                source="https://www.whiteoutsurvival.wiki/heroes/jessie/",
                confidence="high",
                stacking_evidence_level="OFFICIAL_CONFIRMED",
                stacking_evidence_source=OFFICIAL_DUPLICATE_STACKING_SOURCE,
                stacking_evidence_notes="Identical deterministic Damage Dealt skills add in one bucket.",
            ),
        ],
    ),
    "seo-yoon": Hero(
        id="seo-yoon",
        name="Seo-Yoon",
        hero_type="marksman",
        generation=None,
        expedition_skills=[
            skill(
                1,
                "Rallying Beat",
                "attack_up",
                25.0,
                "all_troops",
                source="https://www.whiteoutsurvival.wiki/heroes/seo-yoon/",
                confidence="high",
                notes="Level-5 first expedition skill: all Troops Attack +25%.",
                stacking_evidence_level="COMMUNITY_REPRODUCED",
                stacking_evidence_source=COMMUNITY_BUCKET_TEST_SOURCE,
                stacking_evidence_notes="Attack adds with the same key and multiplies with Damage Dealt in scoring.",
            ),
        ],
    ),
    "jasser": Hero(
        id="jasser",
        name="Jasser",
        hero_type="marksman",
        generation=None,
        expedition_skills=[
            skill(
                1,
                "Tactical Genius",
                "damage_up",
                25.0,
                "all_troops",
                source="https://www.whiteoutsurvival.wiki/heroes/jasser/",
                confidence="high",
                stacking_evidence_level="OFFICIAL_CONFIRMED",
                stacking_evidence_source=OFFICIAL_DUPLICATE_STACKING_SOURCE,
                stacking_evidence_notes="Shares Jessie's friendly/all-troop/Damage Dealt additive bucket.",
            ),
        ],
    ),
    "lumak": Hero(
        id="lumak",
        name="Lumak Bokan",
        hero_type="lancer",
        generation=None,
        expedition_skills=[
            skill(
                1,
                "Tactical Deception",
                "enemy_damage_dealt_down",
                20.0,
                "all_troops",
                affected_side="enemy",
                source="https://www.whiteoutsurvival.wiki/heroes/lumak-bokan/",
                confidence="high",
                stacking_evidence_level="COMMUNITY_UNVERIFIED",
                stacking_evidence_source=COMMUNITY_DEFENSE_MODEL_SOURCE,
                stacking_evidence_notes="Separate enemy Damage Dealt layer; reciprocal operator remains unverified.",
            ),
        ],
    ),
    "ling": Hero(
        id="ling",
        name="Ling Xue",
        hero_type="lancer",
        generation=None,
        expedition_skills=[
            skill(
                1,
                "Fearsome Aura",
                "enemy_attack_down",
                20.0,
                "all_troops",
                affected_side="enemy",
                source="https://www.whiteoutsurvival.wiki/heroes/ling-shuang/",
                confidence="high",
                stacking_evidence_level="COMMUNITY_UNVERIFIED",
                stacking_evidence_source=COMMUNITY_DEFENSE_MODEL_SOURCE,
                stacking_evidence_notes="Separate enemy Attack layer; reciprocal operator remains unverified.",
            ),
        ],
    ),
    "patrick": Hero(
        id="patrick",
        name="Patrick",
        hero_type="lancer",
        generation=None,
        expedition_skills=[
            skill(
                1,
                "Super Nutrients",
                "health_up",
                25.0,
                "all_troops",
                source="https://www.whiteoutsurvival.wiki/heroes/patrick/",
                confidence="high",
                stacking_evidence_level="COMMUNITY_CONSENSUS",
                stacking_evidence_source=OFFICIAL_DUPLICATE_STACKING_SOURCE,
                stacking_evidence_notes="Same-key Health copies are modeled additively.",
            ),
        ],
    ),
    "sergey": Hero(
        id="sergey",
        name="Sergey",
        hero_type="infantry",
        generation=None,
        expedition_skills=[
            skill(
                1,
                "Defender's Edge",
                "damage_taken_down",
                20.0,
                "all_troops",
                source="https://www.whiteoutsurvival.wiki/heroes/sergey/",
                confidence="high",
                stacking_evidence_level="COMMUNITY_UNVERIFIED",
                stacking_evidence_source=COMMUNITY_DEFENSE_MODEL_SOURCE,
                stacking_evidence_notes="Friendly Damage Taken layer; reciprocal operator remains unverified.",
            ),
        ],
    ),
    "flint": Hero(
        id="flint",
        name="Flint",
        hero_type="infantry",
        generation=2,
        expedition_skills=[
            skill(
                1,
                "Pyromaniac",
                "damage_up",
                100.0,
                "infantry",
                source="https://www.whiteoutsurvival.wiki/heroes/flint/",
                confidence="high",
                stacking_evidence_level="COMMUNITY_REPRODUCED",
                stacking_evidence_source=COMMUNITY_BUCKET_TEST_SOURCE,
                stacking_evidence_notes="Infantry-only Damage Dealt is a separate scope factor from all-troop Damage Dealt.",
            ),
        ],
        widget=widget_supported(),
    ),
    "philly": Hero(
        id="philly",
        name="Philly",
        hero_type="lancer",
        generation=2,
        expedition_skills=[
            skill(
                1,
                "Vigor Tactics",
                "attack_up",
                15.0,
                "all_troops",
                source="https://www.whiteoutsurvival.wiki/heroes/philly/",
                confidence="high",
                notes="Compound first expedition skill: all Troops Attack +15% and Defense +10%.",
                effect_components=[
                    component("attack_up", 15.0),
                    component("defense_up", 10.0),
                ],
                stacking_evidence_level="COMMUNITY_REPRODUCED",
                stacking_evidence_source=COMMUNITY_BUCKET_TEST_SOURCE,
                stacking_evidence_notes="Attack and Defense are independent components with distinct canonical keys.",
            ),
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
    "gwen": Hero(
        "gwen",
        "Gwen",
        "marksman",
        5,
        [
            skill(
                1,
                "Eagle Vision",
                "enemy_damage_taken_up",
                25.0,
                "all_troops",
                affected_side="enemy",
                source="https://www.whiteoutsurvival.wiki/heroes/gwen-2/",
                confidence="medium",
                notes="Experimental: tooltip magnitude is modelable, but public tests report mode/turn-dependent effective value.",
                stacking_evidence_level="EXPERIMENTAL_UNVERIFIED",
                stacking_evidence_source="https://www.reddit.com/r/whiteoutsurvival/comments/1t0a62h/can_someone_here_explain_to_me_how_gwens_skill_as/",
                stacking_evidence_notes="Excluded from production recommendations unless explicitly enabled.",
                production_eligible=False,
                experimental=True,
            ),
        ],
        widget_supported(),
    ),
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
        "lumak bokan": "lumak",
        "lumak-bokan": "lumak",
        "ling xue": "ling",
        "ling-xue": "ling",
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
        "expedition_skills": [
            {
                **{key: value for key, value in expedition_skill.__dict__.items() if key != "effect_components"},
                "effect_components": [component.__dict__ for component in expedition_skill.effect_components],
            }
            for expedition_skill in hero.expedition_skills
        ],
        "widget": {
            "supported": hero.widget.supported,
            "effect_type": hero.widget.effect_type,
            "value_pct_by_level": hero.widget.value_pct_by_level,
            "target_scope": hero.widget.target_scope,
            "notes": hero.widget.notes,
        },
    }
