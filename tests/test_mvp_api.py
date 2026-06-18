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
