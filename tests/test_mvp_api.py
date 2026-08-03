from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def sample_army(name="Army", troop_count=100000):
    stats = {
        "attack_pct": 150,
        "defense_pct": 120,
        "health_pct": 180,
        "lethality_pct": 80,
    }
    return {
        "name": name,
        "infantry": stats,
        "lancer": stats,
        "marksman": stats,
        "formation": {"infantry": 0.5, "lancer": 0.2, "marksman": 0.3},
        "troop_count": troop_count,
        "heroes": [
            {"id": "flint", "name": "Flint", "type": "infantry", "stars": 5, "widget_level": 5},
            {"id": "philly", "name": "Philly", "type": "lancer", "stars": 5, "widget_level": 5},
            {"id": "alonso", "name": "Alonso", "type": "marksman", "stars": 5, "widget_level": 5},
        ],
    }


def sample_complete_rally():
    return {
        "objective": "KILL_INFANTRY",
        "leaderHeroes": [
            {"heroId": "hector", "widgetLevel": 6},
            {"heroId": "norah", "widgetLevel": 6},
            {"heroId": "gwen", "widgetLevel": 6},
        ],
        "joinerHeroIds": ["jessie", "jasser", "seo-yoon", "flint"],
        "troopType": "marksman",
    }


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_hero_definitions_are_transparent():
    response = client.get("/hero-definitions")
    assert response.status_code == 200
    body = response.json()
    assert body["heroes"]
    assert "status" in body["heroes"][0]


def test_combat_constants_mark_pending_verification():
    response = client.get("/combat-constants")
    assert response.status_code == 200
    assert response.json()["status"] == "pending verification"


def test_prediction_returns_mvp_metadata_and_warnings():
    response = client.post(
        "/predict-outcome",
        json={"attacker": sample_army("Own"), "defender": sample_army("Enemy", 90000)},
    )
    assert response.status_code == 200
    body = response.json()
    assert "win_probability" in body
    assert body["metadata"]["confidence_level"] == "low"
    assert body["metadata"]["warnings"]


def test_invalid_formation_is_rejected():
    army = sample_army()
    army["formation"] = {"infantry": 0.5, "lancer": 0.5, "marksman": 0.5}
    response = client.post(
        "/predict-outcome",
        json={"attacker": army, "defender": sample_army("Enemy")},
    )
    assert response.status_code == 422


def test_parse_scout_text_extracts_known_fields():
    response = client.post(
        "/parse-scout-text",
        json={"text": "Infantry Attack 123.4 Infantry Defense 55 Lancer Health 88"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["parsed_stats"]["infantry"]["attack_pct"] == 123.4
    assert body["fields_found"] == 3


def test_joiner_recommendation_endpoint_returns_level_5_ranked_result():
    response = client.post(
        "/api/rallies/joiner-recommendations",
        json={
            "objective": "MAX_DAMAGE",
            "joinerCount": 4,
            "allowDuplicateHeroes": True,
            "troopType": "infantry",
            "availableHeroIds": ["jessie", "jasser", "seo-yoon", "flint"],
            "availableHeroCounts": {"jessie": 1, "jasser": 1, "seo-yoon": 1, "flint": 1},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendedJoiners"]) == 4
    assert all(item["skillLevel"] == 5 for item in body["recommendedJoiners"])
    assert body["scores"]["damageImprovementPercentage"] > 0
    assert body["alternatives"] == []


def test_joiner_recommendation_endpoint_rejects_invalid_reduction():
    response = client.post(
        "/api/rallies/joiner-recommendations",
        json={
            "objective": "MAX_DEFENSE",
            "currentBuffs": {"damageTakenReduction": 1.0},
        },
    )
    assert response.status_code == 422


def test_complete_rally_evaluation_endpoint_returns_exact_nine_plus_four_contract():
    response = client.post("/api/rallies/evaluate", json=sample_complete_rally())

    assert response.status_code == 200
    body = response.json()
    assert body["contract"]["leaderSkillSlots"] == 9
    assert body["contract"]["requiredLeaderSkillSlots"] == 9
    assert body["contract"]["joinerContributionSlots"] == 4
    assert body["contract"]["requiredJoinerContributionSlots"] == 4
    assert body["contract"]["complete"] is True
    assert len(body["leaderSkills"]) == 9
    assert len(body["joinerSkills"]) == 4
    assert body["modelCoverage"]["totalSkillSlots"] == 13
    assert body["modelCoverage"]["contractCompleteDoesNotImplyExactCombatModel"] is True


def test_complete_rally_evaluation_endpoint_rejects_fewer_than_four_joiners():
    payload = sample_complete_rally()
    payload["joinerHeroIds"] = payload["joinerHeroIds"][:3]

    response = client.post("/api/rallies/evaluate", json=payload)

    assert response.status_code == 422


def test_complete_rally_plan_endpoint_selects_by_full_nine_plus_four_outcome():
    response = client.post(
        "/api/rallies/optimize-plan",
        json={
            "rallies": [{
                "rallyId": "castle-holder",
                "objective": "GARRISON_BALANCED",
                "leaderHeroes": [
                    {"heroId": "jeronimo", "widgetLevel": 0},
                    {"heroId": "molly", "widgetLevel": 0},
                    {"heroId": "zinman", "widgetLevel": 0},
                ],
                "troopType": "infantry",
                "troopSplit": {"infantry": 0.4, "lancer": 0.3, "marksman": 0.3},
            }],
            "availableHeroIds": [
                "jessie", "jasser", "seo-yoon", "lumak", "ling",
                "patrick", "sergey", "gwen", "philly", "flint",
            ],
            "availableHeroCounts": {
                "jessie": 1, "jasser": 1, "seo-yoon": 1, "lumak": 1, "ling": 1,
                "patrick": 1, "sergey": 1, "gwen": 1, "philly": 1, "flint": 1,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    rally = body["rallies"][0]
    assert body["optimizationKind"] == "GLOBAL_INVENTORY_COMPLETE_9_PLUS_4_EXPECTED_GOAL_LIFT"
    assert {item["heroId"] for item in rally["recommendedJoiners"]} == {
        "flint", "lumak", "patrick", "philly",
    }
    assert rally["evaluation"]["contract"]["leaderSkillSlots"] == 9
    assert rally["evaluation"]["contract"]["joinerContributionSlots"] == 4
    assert rally["evaluation"]["contract"]["complete"] is True
