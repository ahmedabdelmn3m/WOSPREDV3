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
    "normal_attack_damage_up",
    "extra_attack_damage_up",
    "lethality_up",
    "defense_up",
    "health_up",
    "damage_taken_down",
    "normal_attack_dodge_up",
    "enemy_attack_skip",
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
    # Some debuffs are caused only by one friendly troop class (for example,
    # Ahmose's Infantry applies target Damage Taken).  target_scope names the
    # stat/effect subject; source_scope names the friendly triggering row.
    source_scope: str = "all_troops"
    affected_side: str = "friendly"
    stacking_method: str = "ADDITIVE"
    max_stacks: int = 4

    @property
    def value_decimal(self) -> float:
        return self.value_pct / 100.0

    @property
    def canonical_stack_key(self) -> str:
        source_suffix = "" if self.source_scope == "all_troops" else f":source={self.source_scope}"
        return f"{self.affected_side}:{self.target_scope}:{self.effect_type}{source_suffix}"


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
    combat_contexts: Tuple[str, ...] = ("pvp_attack", "garrison", "pve_beast")
    duration_turns: Optional[int] = None
    interval_attacks: Optional[int] = None
    model_status: str = "DIRECT"
    model_notes: str = ""
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
                source_scope=self.target_scope if self.affected_side == "friendly" else "all_troops",
                affected_side=self.affected_side,
                stacking_method=self.stacking_method,
                max_stacks=self.max_stacks,
            ),
        )


@dataclass(frozen=True)
class HeroWidget:
    supported: bool = False
    name: Optional[str] = None
    effect_type: Optional[str] = None
    value_pct_by_level: Optional[Dict[str, float]] = None
    target_scope: Optional[str] = None
    affected_side: str = "friendly"
    combat_contexts: Tuple[str, ...] = ()
    expedition_skill_name: Optional[str] = None
    raw_stat_scope: Optional[str] = None
    raw_lethality_pct_at_level_10: Optional[float] = None
    raw_health_pct_at_level_10: Optional[float] = None
    source: str = "unknown"
    confidence: str = "low"
    notes: str = "Widget values are not verified for this hero."

    def value_at_level(self, level: int) -> float:
        if not self.value_pct_by_level:
            return 0.0
        bounded = max(0, min(10, int(level)))
        return float(self.value_pct_by_level.get(str(bounded), 0.0))


@dataclass(frozen=True)
class Hero:
    id: str
    name: str
    hero_type: str = "unknown"
    generation: Optional[int] = None
    expedition_skills: List[ExpeditionSkill] = field(default_factory=list)
    widget: HeroWidget = field(default_factory=HeroWidget)
    max_expedition_attack_pct: Optional[float] = None
    max_expedition_defense_pct: Optional[float] = None
    rarity: str = "unknown"

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
    combat_contexts: Tuple[str, ...] = ("pvp_attack", "garrison", "pve_beast"),
    duration_turns: Optional[int] = None,
    interval_attacks: Optional[int] = None,
    model_status: str = "DIRECT",
    model_notes: str = "",
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
        combat_contexts=combat_contexts,
        duration_turns=duration_turns,
        interval_attacks=interval_attacks,
        model_status=model_status,
        model_notes=model_notes,
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
    source_scope: str = "all_troops",
    affected_side: str = "friendly",
    stacking_method: str = "ADDITIVE",
    max_stacks: int = 4,
) -> SkillEffectComponent:
    return SkillEffectComponent(
        effect_type=effect_type,
        value_pct=value_pct,
        target_scope=target_scope,
        source_scope=source_scope,
        affected_side=affected_side,
        stacking_method=stacking_method,
        max_stacks=max_stacks,
    )


WIDGET_EXPEDITION_SPECIAL_BY_LEVEL = {
    "0": 0.0,
    "1": 0.0,
    "2": 5.0,
    "3": 5.0,
    "4": 7.5,
    "5": 7.5,
    "6": 10.0,
    "7": 10.0,
    "8": 12.5,
    "9": 12.5,
    "10": 15.0,
}
WIDGET_TIER_SOURCE = "https://www.whiteoutsurvival.wiki/combat-stats-special-bonuses/"


def widget_supported(
    notes: str = "Widget supported; exact per-level values are pending verification.",
    *,
    name: Optional[str] = None,
    expedition_skill_name: Optional[str] = None,
    effect_type: Optional[str] = None,
    target_scope: Optional[str] = "all_troops",
    combat_contexts: Tuple[str, ...] = (),
    raw_stat_scope: Optional[str] = None,
    raw_lethality_pct_at_level_10: Optional[float] = None,
    raw_health_pct_at_level_10: Optional[float] = None,
    source: str = WIDGET_TIER_SOURCE,
    confidence: str = "high",
) -> HeroWidget:
    return HeroWidget(
        supported=True,
        name=name,
        expedition_skill_name=expedition_skill_name,
        effect_type=effect_type,
        value_pct_by_level=dict(WIDGET_EXPEDITION_SPECIAL_BY_LEVEL) if effect_type else None,
        target_scope=target_scope,
        combat_contexts=combat_contexts,
        raw_stat_scope=raw_stat_scope,
        raw_lethality_pct_at_level_10=raw_lethality_pct_at_level_10,
        raw_health_pct_at_level_10=raw_health_pct_at_level_10,
        source=source,
        confidence=confidence,
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


def _official_hero_source(slug: str) -> str:
    return f"https://www.whiteoutsurvival.wiki/heroes/{slug}/"


def _leader_widget(
    hero_type: str,
    name: str,
    expedition_skill_name: str,
    effect_type: str,
    context: str,
    raw_max: float,
    hero_slug: str,
) -> HeroWidget:
    return widget_supported(
        (
            "The Expedition special uses the verified even-level ladder. "
            "Only the level-10 raw Lethality/Health totals are authoritative; "
            "levels 1-9 must not be linearly inferred as exact values."
        ),
        name=name,
        expedition_skill_name=expedition_skill_name,
        effect_type=effect_type,
        target_scope="all_troops",
        combat_contexts=(context,),
        raw_stat_scope=hero_type,
        raw_lethality_pct_at_level_10=raw_max,
        raw_health_pct_at_level_10=raw_max,
        source=_official_hero_source(hero_slug),
    )


def _mythic_hero(
    hero_id: str,
    name: str,
    hero_type: str,
    generation: int,
    base_pct: float,
    expedition_skills: List[ExpeditionSkill],
    widget: HeroWidget,
) -> Hero:
    return Hero(
        id=hero_id,
        name=name,
        hero_type=hero_type,
        generation=generation,
        expedition_skills=expedition_skills,
        widget=widget,
        max_expedition_attack_pct=base_pct,
        max_expedition_defense_pct=base_pct,
        rarity="mythic",
    )


# Current post-December-2025 S1-S5 leader catalogue.  Older community pages
# still expose pre-rework kits; these records deliberately follow the current
# Century Games official Wiki tooltips and keep time/proc uncertainty explicit.
HEROES_BY_ID.update({
    "jeronimo": _mythic_hero(
        "jeronimo", "Jeronimo", "infantry", 1, 260.20,
        [
            skill(1, "Battle Manifesto", "damage_up", 25.0, source=_official_hero_source("jeronimo"), confidence="high"),
            skill(2, "Swordmentor", "attack_up", 25.0, source=_official_hero_source("jeronimo"), confidence="high", applicable_as_joiner=False),
            skill(
                3, "Expert Swordsmanship", "damage_up", 30.0,
                source=_official_hero_source("jeronimo"), confidence="high", applicable_as_joiner=False,
                activation_condition="Active for 2 turns every 4 turns.", activation_probability=0.50,
                duration_turns=2, interval_attacks=4, model_status="PERIODIC_PROXY",
                model_notes="Expected view uses 50% nominal uptime; exact turn order remains stateful.",
            ),
        ],
        _leader_widget("infantry", "Dawnbreak", "Discernment", "attack_up", "pvp_attack", 62.5, "jeronimo"),
    ),
    "natalia": _mythic_hero(
        "natalia", "Natalia", "infantry", 1, 200.16,
        [
            skill(
                1, "Feral Protection", "damage_taken_down", 50.0,
                source=_official_hero_source("natalia"), confidence="high",
                activation_condition="40% chance to reduce all troops' Damage Taken.", activation_probability=0.40,
                model_status="CHANCE_PROXY",
            ),
            skill(2, "Queen of the Wild", "attack_up", 25.0, source=_official_hero_source("natalia"), confidence="high", applicable_as_joiner=False),
            skill(
                3, "Call of the Wild", "damage_up", 25.0,
                source=_official_hero_source("natalia"), confidence="high", applicable_as_joiner=False,
                combat_contexts=("pve_beast",), model_status="CONTEXT_ONLY",
                model_notes="The current tooltip limits this bonus to rallies on beasts; it is excluded from PvP and structure rallies.",
            ),
        ],
        _leader_widget("infantry", "Gale Force", "Invincibles", "lethality_up", "pvp_attack", 55.5, "natalia"),
    ),
    "molly": _mythic_hero(
        "molly", "Molly", "lancer", 1, 200.16,
        [
            skill(
                1, "Snow's Grace", "damage_taken_down", 50.0,
                source=_official_hero_source("molly"), confidence="high",
                activation_condition="40% chance to reduce all troops' Damage Taken.", activation_probability=0.40,
                model_status="CHANCE_PROXY",
            ),
            skill(
                2, "Ice Dominion", "damage_up", 50.0,
                source=_official_hero_source("molly"), confidence="high", applicable_as_joiner=False,
                activation_condition="Each troop attack has a 50% chance to deal 50% more damage.", activation_probability=0.50,
                model_status="CHANCE_PROXY",
            ),
            skill(3, "Youthful Rage", "damage_up", 25.0, source=_official_hero_source("molly"), confidence="high", applicable_as_joiner=False),
        ],
        _leader_widget("lancer", "Yeti Spirit", "Snowy Blessing", "lethality_up", "garrison", 50.0, "molly"),
    ),
    "zinman": _mythic_hero(
        "zinman", "Zinman", "marksman", 1, 200.16,
        [
            skill(
                1, "Implacable", "defense_up", 10.0,
                source=_official_hero_source("zinman"), confidence="high",
                effect_components=[component("defense_up", 10.0), component("health_up", 10.0)],
                notes="All troops Defense +10% and Health +10% at Expedition skill level 5.",
            ),
            skill(
                2, "Bastionist", "unknown", 0.0,
                source=_official_hero_source("zinman"), confidence="high", applicable_as_joiner=False,
                model_status="NON_COMBAT", model_notes="Construction resource cost and building-speed skill; occupies a leader slot but adds no combat buff.",
            ),
            skill(3, "Positional Battler", "lethality_up", 25.0, source=_official_hero_source("zinman"), confidence="high", applicable_as_joiner=False),
        ],
        _leader_widget("marksman", "Woodpecker", "Defend to Attack", "attack_up", "garrison", 50.0, "zinman"),
    ),
    "flint": _mythic_hero(
        "flint", "Flint", "infantry", 2, 240.19,
        [
            skill(1, "Pyromaniac", "damage_up", 100.0, "infantry", source=_official_hero_source("flint"), confidence="high"),
            skill(2, "Burning Resolve", "attack_up", 25.0, source=_official_hero_source("flint"), confidence="high", applicable_as_joiner=False),
            skill(3, "Immolation", "lethality_up", 25.0, source=_official_hero_source("flint"), confidence="high", applicable_as_joiner=False),
        ],
        _leader_widget("infantry", "Dragonbane", "Dragonbreath", "attack_up", "garrison", 60.0, "flint"),
    ),
    "philly": _mythic_hero(
        "philly", "Philly", "lancer", 2, 240.19,
        [
            skill(
                1, "Vigor Tactics", "attack_up", 15.0,
                source=_official_hero_source("philly"), confidence="high",
                effect_components=[component("attack_up", 15.0), component("defense_up", 10.0)],
                notes="All troops Attack +15% and Defense +10% at Expedition skill level 5.",
            ),
            skill(
                2, "Dosage Boost", "normal_attack_damage_up", 200.0,
                source=_official_hero_source("philly"), confidence="high", applicable_as_joiner=False,
                activation_condition="Troop attacks have a 25% chance to deal 200% extra damage.", activation_probability=0.25,
                model_status="CHANCE_PROXY",
            ),
            skill(
                3, "Energizing Shot", "damage_taken_down", 50.0,
                source=_official_hero_source("philly"), confidence="high", applicable_as_joiner=False,
                activation_condition="40% chance to reduce all troops' Damage Taken.", activation_probability=0.40,
                model_status="CHANCE_PROXY",
            ),
        ],
        _leader_widget("lancer", "Pharmacologica", "First Aid Training", "health_up", "garrison", 60.0, "philly"),
    ),
    "alonso": _mythic_hero(
        "alonso", "Alonso", "marksman", 2, 240.19,
        [
            skill(
                1, "Onslaught", "lethality_up", 50.0,
                source=_official_hero_source("alonso"), confidence="medium",
                activation_condition="40% chance to increase all troops' Lethality; public tooltip omits duration.", activation_probability=0.40,
                model_status="CHANCE_DURATION_UNKNOWN",
            ),
            skill(
                2, "Iron Strength", "enemy_damage_dealt_down", 50.0,
                affected_side="enemy", source=_official_hero_source("alonso"), confidence="high", applicable_as_joiner=False,
                activation_condition="Troop attacks have a 20% chance to reduce enemy Damage Dealt for 2 turns.", activation_probability=0.20,
                duration_turns=2, model_status="STATEFUL_PROC",
            ),
            skill(
                3, "Poison Harpoon", "damage_up", 50.0,
                source=_official_hero_source("alonso"), confidence="high", applicable_as_joiner=False,
                activation_condition="Troop attacks have a 50% chance to deal 50% more damage.", activation_probability=0.50,
                model_status="CHANCE_PROXY",
            ),
        ],
        _leader_widget("marksman", "Captain Ahab", "Harpoon Enhancement", "lethality_up", "pvp_attack", 60.0, "alonso"),
    ),
})

HEROES_BY_ID.update({
    "logan": _mythic_hero(
        "logan", "Logan", "infantry", 3, 290.23,
        [
            skill(
                1, "Lion's Might", "enemy_attack_down", 20.0,
                affected_side="enemy", source=_official_hero_source("logan"), confidence="high",
                notes="Current post-rework skill: all enemy troops Attack -20%.",
            ),
            skill(2, "Lion Intimidation", "damage_taken_down", 20.0, source=_official_hero_source("logan"), confidence="high", applicable_as_joiner=False),
            skill(3, "Leader Inspiration", "health_up", 25.0, source=_official_hero_source("logan"), confidence="high", applicable_as_joiner=False),
        ],
        _leader_widget("infantry", "Fists of Steel", "Strong Protection", "defense_up", "garrison", 70.0, "logan"),
    ),
    "mia": _mythic_hero(
        "mia", "Mia", "lancer", 3, 290.23,
        [
            skill(
                1, "Bad Luck Streak", "enemy_damage_taken_up", 50.0,
                affected_side="enemy", source=_official_hero_source("mia"), confidence="medium",
                activation_condition="50% chance to increase damage taken by all enemy troops.", activation_probability=0.50,
                model_status="CHANCE_TIMING_DISPUTED",
                model_notes="The tooltip value is current; public tests disagree on whether the effect covers the following whole turn.",
            ),
            skill(
                2, "Lucky Charm", "damage_up", 50.0,
                source=_official_hero_source("mia"), confidence="high", applicable_as_joiner=False,
                activation_condition="50% chance for all troops to deal 50% more damage.", activation_probability=0.50,
                model_status="CHANCE_PROXY",
            ),
            skill(
                3, "Ritual Deciphering", "damage_taken_down", 50.0,
                source=_official_hero_source("mia"), confidence="high", applicable_as_joiner=False,
                activation_condition="40% chance to reduce all troops' Damage Taken by 50%.", activation_probability=0.40,
                model_status="CHANCE_PROXY",
            ),
        ],
        _leader_widget("lancer", "Fate Crystal", "Rally of Fate", "attack_up", "pvp_attack", 70.0, "mia"),
    ),
    "greg": _mythic_hero(
        "greg", "Greg", "marksman", 3, 290.23,
        [
            skill(
                1, "Sword of Justice", "damage_up", 40.0,
                source=_official_hero_source("greg"), confidence="high",
                activation_condition="20% chance to increase all troops' Damage Dealt for 3 turns.", activation_probability=0.20,
                duration_turns=3, model_status="STATEFUL_PROC",
                model_notes="Whether a repeat proc refreshes or stacks is not officially documented.",
            ),
            skill(
                2, "Deterrence of Law", "enemy_damage_dealt_down", 50.0,
                affected_side="enemy", source=_official_hero_source("greg"), confidence="high", applicable_as_joiner=False,
                activation_condition="20% chance to reduce enemy Damage Dealt for 2 turns.", activation_probability=0.20,
                duration_turns=2, model_status="STATEFUL_PROC",
            ),
            skill(3, "Law and Order", "health_up", 25.0, source=_official_hero_source("greg"), confidence="high", applicable_as_joiner=False),
        ],
        _leader_widget("marksman", "State Edict", "Trumpet of Justice", "health_up", "pvp_attack", 70.0, "greg"),
    ),
    "ahmose": _mythic_hero(
        "ahmose", "Ahmose", "infantry", 4, 370.29,
        [
            skill(
                1, "Viper Formation", "damage_taken_down", 70.0, "infantry",
                source=_official_hero_source("ahmose"), confidence="medium",
                activation_condition="Every fourth Infantry attack is paused; protection lasts 2 turns.", activation_probability=0.50,
                duration_turns=2, interval_attacks=4, model_status="STATEFUL_TRADEOFF",
                model_notes="Expected view uses nominal 2/4 protection uptime but does not price the skipped Infantry attack.",
                effect_components=[
                    component("damage_taken_down", 70.0, "infantry", source_scope="infantry"),
                    component("damage_taken_down", 30.0, "lancer", source_scope="infantry"),
                    component("damage_taken_down", 30.0, "marksman", source_scope="infantry"),
                ],
            ),
            skill(2, "Prayer of Flame", "damage_up", 100.0, "infantry", source=_official_hero_source("ahmose"), confidence="high", applicable_as_joiner=False),
            skill(
                3, "Blade of Light", "normal_attack_damage_up", 60.0, "infantry",
                source=_official_hero_source("ahmose"), confidence="medium", applicable_as_joiner=False,
                notes="Infantry attack damage +60%; its target takes +25% damage for 1 turn.", duration_turns=1,
                effect_components=[
                    component("normal_attack_damage_up", 60.0, "infantry", source_scope="infantry"),
                    component("enemy_damage_taken_up", 25.0, "all_troops", source_scope="infantry", affected_side="enemy"),
                ],
            ),
        ],
        _leader_widget("infantry", "Guardian's Relic", "Oath of Guardian", "health_up", "garrison", 92.5, "ahmose"),
    ),
    "reina": _mythic_hero(
        "reina", "Reina", "lancer", 4, 370.29,
        [
            skill(1, "Assassin's Instinct", "normal_attack_damage_up", 30.0, source=_official_hero_source("reina"), confidence="high"),
            skill(
                2, "Swift Jive", "normal_attack_dodge_up", 20.0,
                source=_official_hero_source("reina"), confidence="high", applicable_as_joiner=False,
                model_status="DODGE_CHANNEL", model_notes="20% chance for all troops to dodge normal attacks; kept separate from Damage Taken.",
            ),
            skill(
                3, "Shadow Blade", "extra_attack_damage_up", 200.0, "lancer",
                source=_official_hero_source("reina"), confidence="medium", applicable_as_joiner=False,
                activation_condition="Lancers have a fixed 25% chance to make an extra attack at 200% damage.", activation_probability=0.25,
                model_status="EXTRA_ATTACK_PROXY",
                model_notes="Whether Assassin's Instinct also amplifies the extra attack is unverified; the engine does not double-apply it.",
            ),
        ],
        _leader_widget("lancer", "Ninjaken - Raikiri", "Fiery Invasion", "lethality_up", "pvp_attack", 92.5, "reina"),
    ),
    "lynn": _mythic_hero(
        "lynn", "Lynn", "marksman", 4, 370.29,
        [
            skill(
                1, "Song of Lion", "damage_up", 50.0,
                source=_official_hero_source("lynn"), confidence="medium",
                activation_condition="40% chance to increase all troops' Damage Dealt; public tooltip omits duration.", activation_probability=0.40,
                model_status="CHANCE_DURATION_UNKNOWN",
            ),
            skill(2, "Melancholic Ballad", "enemy_damage_dealt_down", 20.0, affected_side="enemy", source=_official_hero_source("lynn"), confidence="high", applicable_as_joiner=False),
            skill(
                3, "Oonai Cadenza", "attack_up", 5.0, "marksman",
                source=_official_hero_source("lynn"), confidence="medium", applicable_as_joiner=False,
                activation_condition="Marksmen gain +5% Attack every 3 attacks, stacking until battle end.", interval_attacks=3,
                model_status="STATEFUL_UNBOUNDED",
                model_notes="The number of stacks depends on battle length and counter ownership; no static expected value is asserted.",
            ),
        ],
        _leader_widget("marksman", "Ella's Tear", "Iranon's Determination", "lethality_up", "garrison", 92.5, "lynn"),
    ),
})

HEROES_BY_ID.update({
    "hector": _mythic_hero(
        "hector", "Hector", "infantry", 5, 444.35,
        [
            skill(
                1, "Survival Instincts", "damage_taken_down", 50.0,
                source=_official_hero_source("hector"), confidence="high",
                activation_condition="40% chance to reduce all troops' Damage Taken by 50%.", activation_probability=0.40,
                model_status="CHANCE_PROXY",
            ),
            skill(
                2, "Rampant", "damage_up", 200.0, "infantry",
                source=_official_hero_source("hector"), confidence="high", applicable_as_joiner=False,
                activation_condition="Applies for 10 attacks; each next boost is 85% of the previous one.", activation_probability=0.535411,
                interval_attacks=10, model_status="DECAYING_SEQUENCE_PROXY",
                model_notes="Expected factor is the 10-attack geometric average: Infantry +107.08%, Marksman +53.54%; the ceiling is the first hit.",
                effect_components=[
                    component("damage_up", 200.0, "infantry", source_scope="infantry"),
                    component("damage_up", 100.0, "marksman", source_scope="marksman"),
                ],
            ),
            skill(
                3, "Blitz", "normal_attack_damage_up", 100.0,
                source=_official_hero_source("hector"), confidence="high", applicable_as_joiner=False,
                activation_condition="25% chance for an attack to deal 200% total damage (+100% extra).", activation_probability=0.25,
                model_status="CHANCE_PROXY",
            ),
        ],
        _leader_widget("infantry", "Steel Fangs", "Goliath", "attack_up", "garrison", 111.0, "hector"),
    ),
    "norah": _mythic_hero(
        "norah", "Norah", "lancer", 5, 444.35,
        [
            skill(
                1, "Combined Arms", "damage_up", 15.0, "infantry",
                source=_official_hero_source("gwen"), confidence="high",
                notes="Persistent +15% Damage Dealt and -15% Damage Taken for Infantry and Marksmen; no Lancer benefit.",
                effect_components=[
                    component("damage_up", 15.0, "infantry", source_scope="infantry"),
                    component("damage_taken_down", 15.0, "infantry", source_scope="infantry"),
                    component("damage_up", 15.0, "marksman", source_scope="marksman"),
                    component("damage_taken_down", 15.0, "marksman", source_scope="marksman"),
                ],
            ),
            skill(
                2, "Sneak Strike", "extra_attack_damage_up", 100.0, "lancer",
                source=_official_hero_source("gwen"), confidence="high", applicable_as_joiner=False,
                activation_condition="Lancers have a 20% chance to deal 100% extra area damage on attack.", activation_probability=0.20,
                model_status="EXTRA_ATTACK_PROXY",
            ),
            skill(
                3, "Momentum", "damage_up", 25.0,
                source=_official_hero_source("gwen"), confidence="medium", applicable_as_joiner=False,
                activation_condition="After every 5 Lancer attacks, all troops gain +25% Damage Dealt and -25% Damage Taken for 2 turns.",
                duration_turns=2, interval_attacks=5, model_status="STATEFUL_COUNTER_UNKNOWN",
                model_notes="Attack-counter semantics are not published, so the expected view does not assume a fixed uptime.",
                effect_components=[component("damage_up", 25.0), component("damage_taken_down", 25.0)],
            ),
        ],
        _leader_widget("lancer", "Snow Cruiser", "True Grit", "defense_up", "garrison", 111.0, "gwen"),
    ),
    "gwen": _mythic_hero(
        "gwen", "Gwen", "marksman", 5, 444.35,
        [
            skill(
                1, "Eagle Vision", "enemy_damage_taken_up", 25.0,
                affected_side="enemy", source=_official_hero_source("gwen-2"), confidence="medium",
                notes="Printed passive tooltip is +25% target Damage Taken, but community Bear/PvE and joiner tests conflict.",
                model_status="DISPUTED_TOOLTIP", production_eligible=False, experimental=True,
                stacking_evidence_level="EXPERIMENTAL_UNVERIFIED",
                stacking_evidence_source="https://vortexgaming.io/en/postdetail/679014",
                stacking_evidence_notes="Excluded from deterministic automatic scoring unless disputed effects are explicitly enabled.",
            ),
            skill(
                2, "Air Dominance", "extra_attack_damage_up", 115.0,
                source=_official_hero_source("gwen-2"), confidence="medium", applicable_as_joiner=False,
                activation_condition="Every 5 attacks: +100% event damage and +15% to the next attack from any source.", activation_probability=0.20,
                interval_attacks=5, model_status="PERIODIC_EVENT_PROXY",
                model_notes="Expected view treats the two event pieces as +23% per five-attack cycle; it is not a persistent +115% buff.",
            ),
            skill(
                3, "Blastmaster", "extra_attack_damage_up", 50.0, "marksman",
                source=_official_hero_source("gwen-2"), confidence="high", applicable_as_joiner=False,
                activation_condition="Marksmen deal 50% extra area damage every 4 attacks.", activation_probability=0.25,
                interval_attacks=4, model_status="PERIODIC_EVENT_PROXY",
            ),
        ],
        _leader_widget("marksman", "Wings of Hope", "Marauder", "lethality_up", "pvp_attack", 111.0, "gwen-2"),
    ),
})

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
        "rarity": hero.rarity,
        "max_expedition_attack_pct": hero.max_expedition_attack_pct,
        "max_expedition_defense_pct": hero.max_expedition_defense_pct,
        "expedition_skills": [
            {
                **{key: value for key, value in expedition_skill.__dict__.items() if key != "effect_components"},
                "effect_components": [component.__dict__ for component in expedition_skill.effect_components],
            }
            for expedition_skill in hero.expedition_skills
        ],
        "widget": dict(hero.widget.__dict__),
    }
