"""Regression tests for the complete 9-leader-skill + 4-joiner contract."""

from collections import Counter
from pathlib import Path

import pytest

from core_engine.rally_evaluation import RallyEvaluationService
from core_engine.joiner_recommendation import JoinerRecommendationService
from hero_data import HEROES_BY_ID


SERVICE = RallyEvaluationService()
JOINER_ONLY_SERVICE = JoinerRecommendationService()
JOINER_POOL = [
    "jessie",
    "jasser",
    "seo-yoon",
    "lumak",
    "ling",
    "patrick",
    "sergey",
    "gwen",
    "philly",
    "flint",
]


def _leader(hero_id: str, widget_level: int = 0) -> dict:
    return {"hero_id": hero_id, "widget_level": widget_level}


def _evaluate(
    objective: str = "MAX_DAMAGE",
    leaders: list[dict] | None = None,
    joiners: list[str] | None = None,
    **kwargs,
) -> dict:
    return SERVICE.evaluate(
        objective=objective,
        leader_heroes=leaders
        or [_leader("jeronimo"), _leader("molly"), _leader("zinman")],
        joiner_hero_ids=joiners or ["jessie"] * 4,
        **kwargs,
    )


def _skill_by_name(result: dict, collection: str, name: str) -> dict:
    return next(skill for skill in result[collection] if skill["skillName"] == name)


def _plan_rally(rally_id: str, objective: str) -> dict:
    return {
        "rally_id": rally_id,
        "objective": objective,
        "leader_heroes": [_leader("jeronimo"), _leader("molly"), _leader("zinman")],
        "troop_type": "infantry",
        "troop_split": {"infantry": 0.4, "lancer": 0.3, "marksman": 0.3},
        "include_disputed_skills": False,
    }


def test_complete_rally_contains_nine_leader_skills_and_four_joiner_primaries():
    result = _evaluate(
        objective="KILL_INFANTRY",
        leaders=[_leader("hector", 6), _leader("norah", 6), _leader("gwen", 6)],
        joiners=["jessie", "jasser", "seo-yoon", "flint"],
    )

    assert result["contract"]["leaderHeroCount"] == 3
    assert result["contract"]["leaderSkillSlots"] == 9
    assert result["contract"]["requiredLeaderSkillSlots"] == 9
    assert result["contract"]["joinerContributionSlots"] == 4
    assert result["contract"]["requiredJoinerContributionSlots"] == 4
    assert result["contract"]["complete"] is True
    assert result["goalAssessment"]["completeContract"] is True
    assert result["calculationKind"] == "NORMALIZED_SKILL_STACK_INDEX"
    assert result["modelCoverage"]["totalSkillSlots"] == 13
    assert result["modelCoverage"]["contractCompleteDoesNotImplyExactCombatModel"] is True
    assert result["reportPolicy"]["sharedObservedStatVectorAcrossTroops"] is True
    assert len(result["leaderSkills"]) == 9
    assert len(result["joinerSkills"]) == 4
    assert Counter(skill["heroId"] for skill in result["leaderSkills"]) == {
        "hector": 3,
        "norah": 3,
        "gwen": 3,
    }
    assert {skill["slot"] for skill in result["leaderSkills"]} == {1, 2, 3}
    assert [skill["slot"] for skill in result["joinerSkills"]] == [1, 1, 1, 1]


@pytest.mark.parametrize("joiners", [["jessie"] * 3, ["jessie"] * 5])
def test_evaluator_rejects_any_joiner_count_other_than_four(joiners):
    with pytest.raises(ValueError, match="exactly 4"):
        _evaluate(joiners=joiners)


def test_leader_march_requires_one_s1_to_s5_mythic_of_each_troop_type():
    accepted = _evaluate(
        leaders=[_leader("natalia"), _leader("reina"), _leader("gwen")],
    )
    assert [hero["heroType"] for hero in accepted["leaderHeroes"]] == [
        "infantry",
        "lancer",
        "marksman",
    ]

    with pytest.raises(ValueError, match="exactly one Infantry"):
        _evaluate(leaders=[_leader("jeronimo"), _leader("flint"), _leader("gwen")])

    with pytest.raises(ValueError, match="S1-S5 Mythic"):
        _evaluate(leaders=[_leader("natalia"), _leader("jessie"), _leader("zinman")])


def test_all_configured_s1_to_s5_mythic_candidates_have_three_skill_slots():
    candidates = [
        hero
        for hero in HEROES_BY_ID.values()
        if hero.rarity == "mythic" and hero.generation in range(1, 6)
    ]

    assert len(candidates) == 16
    for hero in candidates:
        assert hero.hero_type in {"infantry", "lancer", "marksman"}
        assert [skill.slot for skill in hero.expedition_skills] == [1, 2, 3]
        assert hero.widget.supported is True
        assert hero.widget.expedition_skill_name


@pytest.mark.parametrize(
    ("level", "expected_pct"),
    [(0, 0.0), (1, 0.0), (2, 5.0), (3, 5.0), (4, 7.5), (6, 10.0), (8, 12.5), (10, 15.0)],
)
def test_widget_expedition_special_uses_verified_even_level_ladder(level, expected_pct):
    assert HEROES_BY_ID["gwen"].widget.value_at_level(level) == expected_pct


def test_only_widgets_matching_the_battle_context_are_active_and_raw_stats_are_not_reapplied():
    leaders = [_leader("hector", 10), _leader("norah", 6), _leader("gwen", 6)]
    attack = _evaluate(objective="MAX_DAMAGE", leaders=leaders)
    garrison = _evaluate(objective="GARRISON_HOLD", leaders=leaders)

    attack_widgets = {widget["heroId"]: widget for widget in attack["widgets"]}
    garrison_widgets = {widget["heroId"]: widget for widget in garrison["widgets"]}

    assert attack_widgets["gwen"]["activeForContext"] is True
    assert attack_widgets["gwen"]["valuePct"] == 10.0
    assert attack_widgets["hector"]["status"] == "wrong_context"
    assert attack_widgets["norah"]["status"] == "wrong_context"

    assert garrison_widgets["hector"]["activeForContext"] is True
    assert garrison_widgets["hector"]["valuePct"] == 15.0
    assert garrison_widgets["norah"]["activeForContext"] is True
    assert garrison_widgets["gwen"]["status"] == "wrong_context"

    assert attack_widgets["hector"]["rawStats"]["selectedLevelValuePct"] == 111.0
    assert attack_widgets["hector"]["rawStats"]["appliedToScore"] is False
    assert attack_widgets["norah"]["rawStats"]["selectedLevelValuePct"] is None


def test_conditional_skills_produce_ordered_floor_expected_and_ceiling_scenarios():
    result = _evaluate()

    damage_ratios = [result["scenarios"][name]["damageRatio"] for name in ("floor", "expected", "ceiling")]
    defense_ratios = [result["scenarios"][name]["defenseRatio"] for name in ("floor", "expected", "ceiling")]
    goal_lifts = [
        result["goalAssessment"][name]
        for name in ("floorLiftPct", "expectedLiftPct", "ceilingLiftPct")
    ]

    assert damage_ratios[0] < damage_ratios[1] < damage_ratios[2]
    assert defense_ratios[0] < defense_ratios[1] < defense_ratios[2]
    assert goal_lifts[0] < goal_lifts[1] < goal_lifts[2]


def test_beast_only_and_noncombat_skills_fill_slots_but_never_score_in_pvp():
    result = _evaluate(leaders=[_leader("natalia"), _leader("molly"), _leader("zinman")])
    beast_skill = _skill_by_name(result, "leaderSkills", "Call of the Wild")
    noncombat_skill = _skill_by_name(result, "leaderSkills", "Bastionist")

    assert result["contract"]["leaderSkillSlots"] == 9
    assert beast_skill["combatContexts"] == ["pve_beast"]
    assert noncombat_skill["modelStatus"] == "NON_COMBAT"
    for scenario in result["scenarios"].values():
        assert beast_skill["recordId"] not in scenario["appliedRecordIds"]
        assert noncombat_skill["recordId"] not in scenario["appliedRecordIds"]


def test_gwen_disputed_effect_requires_opt_in_and_is_still_ceiling_only():
    joiners = ["gwen", "patrick", "patrick", "patrick"]
    excluded = _evaluate(joiners=joiners)
    included = _evaluate(joiners=joiners, include_disputed_skills=True)
    gwen_record = _skill_by_name(excluded, "joinerSkills", "Eagle Vision")["recordId"]

    assert gwen_record not in excluded["scenarios"]["floor"]["appliedRecordIds"]
    assert gwen_record not in included["scenarios"]["floor"]["appliedRecordIds"]
    assert gwen_record not in included["scenarios"]["expected"]["appliedRecordIds"]
    assert gwen_record in included["scenarios"]["ceiling"]["appliedRecordIds"]
    assert included["scenarios"]["floor"]["damageRatio"] == excluded["scenarios"]["floor"]["damageRatio"]
    assert included["scenarios"]["expected"]["damageRatio"] == excluded["scenarios"]["expected"]["damageRatio"]
    assert included["scenarios"]["ceiling"]["damageRatio"] == pytest.approx(
        excluded["scenarios"]["ceiling"]["damageRatio"] * 1.25
    )
    assert included["modelCoverage"]["experimentalCeilingOnlyRecordIds"] == [gwen_record]
    assert any("Disputed tooltip effects" in warning for warning in excluded["warnings"])


def test_deterministic_duplicates_add_but_conditional_proc_chances_remain_separate():
    leaders = [_leader("logan"), _leader("philly"), _leader("gwen")]
    deterministic = _evaluate(leaders=leaders, joiners=["jessie"] * 4)
    deterministic_rows = [
        row
        for row in deterministic["scenarios"]["floor"]["stackBuckets"]
        if row["troop"] == "infantry"
        and row["effectType"] == "damage_up"
        and row["conditionalRecord"] is None
    ]

    assert len(deterministic_rows) == 1
    assert deterministic_rows[0]["combinedPct"] == 100.0

    conditional = _evaluate(
        objective="MAX_DEFENSE",
        leaders=[_leader("flint"), _leader("reina"), _leader("zinman")],
        joiners=["natalia"] * 4,
    )
    expected_natalia_rows = [
        row
        for row in conditional["scenarios"]["expected"]["stackBuckets"]
        if row["conditionalRecord"] and "natalia" in row["conditionalRecord"]
    ]
    ceiling_natalia_rows = [
        row
        for row in conditional["scenarios"]["ceiling"]["stackBuckets"]
        if row["conditionalRecord"] and "natalia" in row["conditionalRecord"]
    ]

    assert len(expected_natalia_rows) == 4
    assert len({row["conditionalRecord"] for row in expected_natalia_rows}) == 4
    assert {row["combinedPct"] for row in expected_natalia_rows} == {20.0}
    assert len(ceiling_natalia_rows) == 4
    assert {row["combinedPct"] for row in ceiling_natalia_rows} == {50.0}
    expected_infantry = conditional["scenarios"]["expected"]["perTroop"]["infantry"]
    ceiling_infantry = conditional["scenarios"]["ceiling"]["perTroop"]["infantry"]
    assert expected_infantry["reductionFactors"]["damageTaken"] == pytest.approx(1.8)
    assert ceiling_infantry["reductionFactors"]["damageTaken"] == pytest.approx(3.0)
    assert expected_infantry["incomingDamageMultiplier"] is None
    assert expected_infantry["incomingDamageMultiplierProxy"] == pytest.approx(1 / 1.8)
    assert expected_infantry["expectedDefenseIndexProxy"] is True
    assert "DO NOT SUM PROC CHANCE" in conditional["stackingPolicy"]["conditionalDuplicates"]


def test_normal_and_extra_attack_contributions_add_inside_one_event_damage_channel():
    result = _evaluate(
        objective="KILL_MARKSMEN",
        leaders=[_leader("hector"), _leader("reina"), _leader("gwen")],
        joiners=["patrick"] * 4,
    )

    lancer = result["scenarios"]["expected"]["perTroop"]["lancer"]
    # Reina's always-on +30%, her 25% x +200% event (+50%), Hector's
    # 25% x +100% event (+25%), and Gwen's 1-in-5 +115% event (+23%).
    assert lancer["eventDamageChannelFactor"] == pytest.approx(2.28)
    assert "DO NOT ASSUME EVENTS AMPLIFY" in result["stackingPolicy"]["normalAndExtraAttackEvents"]


def test_duration_unknown_and_unbounded_state_skills_are_excluded_from_expected_scenario():
    result = _evaluate(
        leaders=[_leader("flint"), _leader("mia"), _leader("lynn")],
        joiners=["patrick"] * 4,
    )
    song = _skill_by_name(result, "leaderSkills", "Song of Lion")
    cadenza = _skill_by_name(result, "leaderSkills", "Oonai Cadenza")

    expected_ids = result["scenarios"]["expected"]["appliedRecordIds"]
    ceiling_ids = result["scenarios"]["ceiling"]["appliedRecordIds"]
    assert song["recordId"] not in expected_ids
    assert cadenza["recordId"] not in expected_ids
    assert song["recordId"] in ceiling_ids
    assert cadenza["recordId"] not in ceiling_ids
    assert song["recordId"] in result["modelCoverage"]["expectedConditionalUnknownRecordIds"]
    assert cadenza["recordId"] in result["modelCoverage"]["expectedConditionalUnknownRecordIds"]


def test_triggering_troop_scope_does_not_hide_ahmose_protection_from_other_rows():
    result = _evaluate(
        objective="MAX_DEFENSE",
        leaders=[_leader("ahmose"), _leader("reina"), _leader("lynn")],
        joiners=["patrick"] * 4,
        troop_split={"infantry": 1, "lancer": 1, "marksman": 1},
    )
    expected = result["scenarios"]["expected"]["perTroop"]
    viper = _skill_by_name(result, "leaderSkills", "Viper Formation")

    assert expected["infantry"]["reductionFactors"]["damageTaken"] == pytest.approx(1.35)
    assert expected["lancer"]["reductionFactors"]["damageTaken"] == pytest.approx(1.15)
    assert expected["marksman"]["reductionFactors"]["damageTaken"] == pytest.approx(1.15)
    assert viper["recordId"] in result["modelCoverage"]["unpricedTradeoffRecordIds"]


@pytest.mark.parametrize(
    ("objective", "joiner_only_ids", "complete_stack_ids"),
    [
        (
            "GARRISON_BALANCED",
            {"flint", "jasser", "patrick", "philly"},
            {"flint", "lumak", "patrick", "philly"},
        ),
        (
            "COUNTER_BREAK",
            {"flint", "jasser", "jessie", "seo-yoon"},
            {"flint", "jessie", "philly", "seo-yoon"},
        ),
    ],
)
def test_optimizer_ranks_the_complete_nine_plus_four_stack_not_joiners_alone(
    objective, joiner_only_ids, complete_stack_ids
):
    counts = {hero_id: 1 for hero_id in JOINER_POOL}
    joiner_only = JOINER_ONLY_SERVICE.recommend(
        objective=objective,
        joiner_count=4,
        allow_duplicate_heroes=True,
        troop_type="infantry",
        troop_split={"infantry": 0.4, "lancer": 0.3, "marksman": 0.3},
        available_hero_ids=JOINER_POOL,
        available_hero_counts=counts,
        excluded_hero_ids=["gwen"],
        minimum_skill_level=5,
        conditional_evaluation="EXCLUDED",
    )
    optimized = SERVICE.optimize_plan(
        [_plan_rally("rally-1", objective)],
        JOINER_POOL,
        counts,
    )
    rally = optimized["rallies"][0]

    assert {item["heroId"] for item in joiner_only["recommendedJoiners"]} == joiner_only_ids
    assert {item["heroId"] for item in rally["recommendedJoiners"]} == complete_stack_ids
    assert rally["evaluation"]["contract"]["complete"] is True
    assert rally["evaluation"]["contract"]["leaderSkillSlots"] == 9
    assert rally["evaluation"]["contract"]["joinerContributionSlots"] == 4
    assert rally["evaluation"]["modelCoverage"]["totalSkillSlots"] == 13


def test_global_optimizer_beats_priority_greedy_while_respecting_shared_inventory():
    counts = {hero_id: 1 for hero_id in JOINER_POOL}
    rallies = [
        _plan_rally("garrison", "GARRISON_BALANCED"),
        _plan_rally("counter", "COUNTER_BREAK"),
    ]
    global_plan = SERVICE.optimize_plan(rallies, JOINER_POOL, counts)

    first_only = SERVICE.optimize_plan([rallies[0]], JOINER_POOL, counts)
    first_ids = [item["heroId"] for item in first_only["rallies"][0]["recommendedJoiners"]]
    greedy_remaining = dict(counts)
    for hero_id in first_ids:
        greedy_remaining[hero_id] -= 1
    second_only = SERVICE.optimize_plan([rallies[1]], JOINER_POOL, greedy_remaining)
    greedy_total = (
        first_only["rallies"][0]["expectedGoalLiftPct"]
        + second_only["rallies"][0]["expectedGoalLiftPct"]
    )

    assigned = [
        item["heroId"]
        for rally in global_plan["rallies"]
        for item in rally["recommendedJoiners"]
    ]
    assert global_plan["optimizationKind"] == "GLOBAL_INVENTORY_COMPLETE_9_PLUS_4_EXPECTED_GOAL_LIFT"
    assert global_plan["completedRallies"] == 2
    assert len(assigned) == 8
    assert len(set(assigned)) == 8
    assert global_plan["totalExpectedGoalLiftPct"] > greedy_total
    assert all(rally["evaluation"]["contract"]["complete"] for rally in global_plan["rallies"])


def test_global_optimizer_is_caller_order_invariant_and_maps_results_back():
    counts = {hero_id: 1 for hero_id in JOINER_POOL}
    garrison = {**_plan_rally("garrison", "GARRISON_BALANCED"), "priority_weight": 1.2}
    counter = {**_plan_rally("counter", "COUNTER_BREAK"), "priority_weight": 1.0}

    forward = SERVICE.optimize_plan([garrison, counter], JOINER_POOL, counts)
    reverse = SERVICE.optimize_plan([counter, garrison], JOINER_POOL, counts)

    def assignments(result):
        return {
            rally["rallyId"]: tuple(sorted(item["heroId"] for item in rally["recommendedJoiners"]))
            for rally in result["rallies"]
        }

    assert [rally["rallyId"] for rally in forward["rallies"]] == ["garrison", "counter"]
    assert [rally["rallyId"] for rally in reverse["rallies"]] == ["counter", "garrison"]
    assert assignments(forward) == assignments(reverse)
    assert forward["weightedExpectedGoalLiftPct"] == pytest.approx(
        reverse["weightedExpectedGoalLiftPct"]
    )


def test_global_optimizer_marks_inventory_shortage_incomplete_instead_of_scoring_under_four():
    available = JOINER_POOL[:7]
    result = SERVICE.optimize_plan(
        [_plan_rally("first", "GARRISON_BALANCED"), _plan_rally("second", "COUNTER_BREAK")],
        available,
        {hero_id: 1 for hero_id in available},
    )

    assert result["completedRallies"] == 1
    assert sum(1 for rally in result["rallies"] if rally["complete"]) == 1
    incomplete = next(rally for rally in result["rallies"] if not rally["complete"])
    assert incomplete["recommendedJoiners"] == []
    assert incomplete["evaluation"] is None
    assert "exactly four" in incomplete["warnings"][0]


@pytest.mark.parametrize(
    ("objective", "joiners"),
    [
        ("KILL_INFANTRY", ("jessie", "seo-yoon", "seo-yoon", "seo-yoon")),
        ("GARRISON_HOLD", ("lumak", "ling", "patrick", "patrick")),
    ],
)
def test_fast_full_stack_ranking_is_exactly_the_public_evaluator_projection(objective, joiners):
    counts = {hero_id: 3 for hero_id in JOINER_POOL}
    rally = _plan_rally("rank-check", objective)
    ranked = SERVICE._rank_complete_joiner_lineups(rally, JOINER_POOL, counts)
    fast = next(item for item in ranked if item["hero_ids"] == joiners)
    full = SERVICE.evaluate(joiner_hero_ids=joiners, **{
        key: value for key, value in rally.items() if key != "rally_id"
    })

    assert fast["floor_lift_pct"] == pytest.approx(full["goalAssessment"]["floorLiftPct"])
    assert fast["expected_lift_pct"] == pytest.approx(full["goalAssessment"]["expectedLiftPct"])
    assert fast["ceiling_lift_pct"] == pytest.approx(full["goalAssessment"]["ceilingLiftPct"])


def test_rtc_uses_global_full_stack_endpoint_and_preserves_live_leader_selections():
    root = Path(__file__).resolve().parents[1]
    rtc = (root / "RTC.html").read_text(encoding="utf-8")
    frontend_rtc = (root / "frontend" / "RTC.html").read_text(encoding="utf-8")

    assert rtc == frontend_rtc
    assert "/api/rallies/optimize-plan" in rtc
    assert "globally optimized 9+4 stacks" in rtc
    batch_loader = rtc.split("async function loadBackendJoinerRecommendations", 1)[1].split(
        "function sampleEnemies", 1
    )[0]
    assert "const ordered = leaders;" in batch_loader
    assert "joinerPlanQuotas(leaders)" not in batch_loader
    assert "leader.rallyLeaderHeroes.splice" in rtc
    assert rtc.count(
        "const selection = ensureLeaderJoinerProfile(leader).rallyLeaderHeroes[leaderTypes.indexOf(type)];"
    ) == 2
