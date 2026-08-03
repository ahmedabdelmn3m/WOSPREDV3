"""Simple live API smoke check for WOSPREDV3.

This checks API availability from a terminal. It does not replace qa.html,
because only the browser QA page can catch browser CORS failures.
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API_URL = "https://wospredv3-production.up.railway.app"
DEFAULT_ORIGIN = "https://wospredv-3.vercel.app"
EXPECTED_RALLY_SCENARIOS = ("floor", "expected", "ceiling")
EXPECTED_RALLY_OPTIMIZATION_KIND = "GLOBAL_INVENTORY_COMPLETE_9_PLUS_4_EXPECTED_GOAL_LIFT"


def sample_army(name: str, troop_count: int) -> dict:
    stats = {
        "attack_pct": 150,
        "defense_pct": 120,
        "health_pct": 180,
        "lethality_pct": 80,
    }
    return {
        "name": name,
        "infantry": dict(stats),
        "lancer": dict(stats),
        "marksman": dict(stats),
        "formation": {"infantry": 0.5, "lancer": 0.2, "marksman": 0.3},
        "troop_count": troop_count,
        "heroes": [
            {"id": "flint", "name": "Flint", "type": "infantry", "stars": 5, "widget_level": 5},
            {"id": "philly", "name": "Philly", "type": "lancer", "stars": 5, "widget_level": 5},
            {"id": "alonso", "name": "Alonso", "type": "marksman", "stars": 5, "widget_level": 5},
        ],
    }


def sample_complete_rally() -> dict:
    """Return a realistic S5 leader march with four modeled joiner skills."""

    return {
        "objective": "KILL_INFANTRY",
        "leaderHeroes": [
            {"heroId": "hector", "widgetLevel": 6},
            {"heroId": "norah", "widgetLevel": 6},
            {"heroId": "gwen", "widgetLevel": 6},
        ],
        "joinerHeroIds": ["jessie", "jasser", "seo-yoon", "flint"],
        "troopType": "marksman",
        "enemyTroopType": "infantry",
        "baseStats": {
            "attack": 765.4,
            "defense": 692.1,
            "health": 813.8,
            "lethality": 731.6,
        },
        "currentBuffs": {
            "attack": 0.18,
            "defense": 0.12,
            "health": 0.15,
            "lethality": 0.16,
            "damageDealt": 0.08,
            "damageTakenReduction": 0.05,
        },
        "enemyStats": {
            "attack": 742.0,
            "defense": 710.0,
            "health": 835.0,
            "lethality": 705.0,
        },
        "troopSplit": {"infantry": 0.5, "lancer": 0.2, "marksman": 0.3},
    }


def sample_complete_rally_plan() -> dict:
    """Return two complete leader marches sharing enough inventory for 4 joins each."""

    attack_rally = sample_complete_rally()
    attack_rally.pop("joinerHeroIds")
    attack_rally.update({"rallyId": "qa-infantry-target", "priorityWeight": 1.2})

    garrison_rally = {
        "rallyId": "qa-garrison-hold",
        "priorityWeight": 1.0,
        "objective": "GARRISON_BALANCED",
        "leaderHeroes": [
            {"heroId": "jeronimo", "widgetLevel": 6},
            {"heroId": "molly", "widgetLevel": 6},
            {"heroId": "zinman", "widgetLevel": 6},
        ],
        "troopType": "infantry",
        "baseStats": dict(attack_rally["baseStats"]),
        "currentBuffs": dict(attack_rally["currentBuffs"]),
        "enemyStats": dict(attack_rally["enemyStats"]),
        "troopSplit": {"infantry": 0.6, "lancer": 0.2, "marksman": 0.2},
    }

    return {
        "rallies": [attack_rally, garrison_rally],
        "availableHeroIds": ["jessie", "jasser", "seo-yoon", "flint"],
        "availableHeroCounts": {
            "jessie": 2,
            "jasser": 2,
            "seo-yoon": 2,
            "flint": 2,
        },
        "alternativeCount": 1,
    }


def request_json(
    base_url: str,
    method: str,
    path: str,
    payload: dict | None = None,
    origin: str | None = None,
) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if origin:
        headers["Origin"] = origin
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers=headers,
    )
    with urlopen(request, timeout=30) as response:
        status = response.getcode()
        if not 200 <= status < 300:
            raise ValueError(f"Unexpected HTTP status {status} for {method} {path}.")
        if origin:
            allowed_origin = response.headers.get("Access-Control-Allow-Origin")
            if allowed_origin not in {origin, "*"}:
                raise ValueError(
                    f"CORS response for {method} {path} did not allow {origin!r}; "
                    f"received {allowed_origin!r}."
                )
        return json.loads(response.read().decode("utf-8"))


def assert_complete_rally_response(body: dict) -> None:
    """Assert the public 9+4 response contract and scenario audit structure."""

    contract = body["contract"]
    assert contract["leaderSkillSlots"] == 9, contract
    assert contract["requiredLeaderSkillSlots"] == 9, contract
    assert contract["joinerContributionSlots"] == 4, contract
    assert contract["requiredJoinerContributionSlots"] == 4, contract
    assert contract["complete"] is True, contract
    assert contract["completeMeaning"] == "STRUCTURAL_9_LEADER_SKILLS_PLUS_4_JOINER_PRIMARY_SKILLS"
    assert isinstance(contract["ruleSource"], str) and contract["ruleSource"].startswith("https://")

    assert len(body["leaderSkills"]) == 9
    assert len(body["joinerSkills"]) == 4
    assert body["modelCoverage"]["totalSkillSlots"] == 13
    assert body["calculationKind"] == "NORMALIZED_SKILL_STACK_INDEX"
    assert body["goalAssessment"]["completeContract"] is True

    assert set(body["scenarios"]) == set(EXPECTED_RALLY_SCENARIOS)
    assert set(body["scenarioPolicy"]) == set(EXPECTED_RALLY_SCENARIOS)
    for scenario_name in EXPECTED_RALLY_SCENARIOS:
        scenario = body["scenarios"][scenario_name]
        assert isinstance(scenario["damageRatio"], (int, float)), scenario_name
        assert isinstance(scenario["defenseRatio"], (int, float)), scenario_name
        assert isinstance(scenario["appliedRecordIds"], list), scenario_name
        assert isinstance(scenario["stackBuckets"], list), scenario_name
        assert isinstance(scenario["perTroop"], dict), scenario_name
        assert body["scenarioPolicy"][scenario_name], scenario_name

    report_source = body["reportPolicy"]["source"]
    assert isinstance(report_source, str) and report_source.startswith("https://")


def assert_complete_rally_plan_response(body: dict, expected_rally_ids: set[str]) -> None:
    """Assert the global optimizer completed every requested exact 9+4 rally."""

    assert body["optimizationKind"] == EXPECTED_RALLY_OPTIMIZATION_KIND
    assert body["rankingScenario"] == "expected"
    assert body["requestedRallies"] == len(expected_rally_ids)
    assert body["completedRallies"] == body["requestedRallies"]
    assert isinstance(body["rankingPolicy"], str) and "exactly 4 joiner skills" in body["rankingPolicy"]

    rallies = body["rallies"]
    assert len(rallies) == len(expected_rally_ids)
    assert {rally["rallyId"] for rally in rallies} == expected_rally_ids
    for rally in rallies:
        assert rally["complete"] is True, rally
        assert len(rally["recommendedJoiners"]) == 4, rally
        assert all(joiner.get("heroId") for joiner in rally["recommendedJoiners"]), rally
        assert_complete_rally_response(rally["evaluation"])


def check(name: str, fn) -> bool:
    try:
        fn()
        print(f"PASS {name}")
        return True
    except (AssertionError, HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        print(f"FAIL {name}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live WOSPREDV3 API contract checks.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API base URL to check.")
    parser.add_argument(
        "--origin",
        default=DEFAULT_ORIGIN,
        help="Frontend Origin header to send and require in CORS responses.",
    )
    args = parser.parse_args()
    api_url = args.api_url.rstrip("/")
    origin = args.origin.rstrip("/")

    def request(method: str, path: str, payload: dict | None = None) -> dict:
        return request_json(api_url, method, path, payload, origin=origin)

    attacker = sample_army("QA Own", 150000)
    defender = sample_army("QA Enemy", 90000)
    battle_payload = {
        "attacker": attacker,
        "defender": defender,
        "max_rounds": 12,
        "simulation_mode": "expected_value",
    }
    optimizer_payload = {"own_army": attacker, "enemy_army": defender, "max_rounds": 12}
    rally_payload = sample_complete_rally()
    rally_plan_payload = sample_complete_rally_plan()

    checks = [
        check("GET /", lambda: request("GET", "/")["service"]),
        check("GET /model-accuracy", lambda: request("GET", "/model-accuracy")["note"]),
        check("POST /predict-outcome", lambda: request("POST", "/predict-outcome", battle_payload)["win_probability"]),
        check("POST /reverse-optimize", lambda: request("POST", "/reverse-optimize", {**optimizer_payload, "target_win_probability": 0.51})["current_win_probability"]),
        check("POST /formation/optimize", lambda: request("POST", "/formation/optimize", optimizer_payload)["best_formation"]),
        check(
            "POST /api/rallies/evaluate (9+4 contract)",
            lambda: assert_complete_rally_response(
                request("POST", "/api/rallies/evaluate", rally_payload)
            ),
        ),
        check(
            "POST /api/rallies/optimize-plan (multi-rally exact 9+4 contract)",
            lambda: assert_complete_rally_plan_response(
                request("POST", "/api/rallies/optimize-plan", rally_plan_payload),
                {rally["rallyId"] for rally in rally_plan_payload["rallies"]},
            ),
        ),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
