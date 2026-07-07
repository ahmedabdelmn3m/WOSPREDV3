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


def request_json(base_url: str, method: str, path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def check(name: str, fn) -> bool:
    try:
        fn()
        print(f"PASS {name}")
        return True
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        print(f"FAIL {name}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    args = parser.parse_args()
    api_url = args.api_url.rstrip("/")

    attacker = sample_army("QA Own", 150000)
    defender = sample_army("QA Enemy", 90000)
    battle_payload = {
        "attacker": attacker,
        "defender": defender,
        "max_rounds": 12,
        "simulation_mode": "expected_value",
    }
    optimizer_payload = {"own_army": attacker, "enemy_army": defender, "max_rounds": 12}

    checks = [
        check("GET /", lambda: request_json(api_url, "GET", "/")["service"]),
        check("GET /model-accuracy", lambda: request_json(api_url, "GET", "/model-accuracy")["note"]),
        check("POST /predict-outcome", lambda: request_json(api_url, "POST", "/predict-outcome", battle_payload)["win_probability"]),
        check("POST /reverse-optimize", lambda: request_json(api_url, "POST", "/reverse-optimize", {**optimizer_payload, "target_win_probability": 0.51})["current_win_probability"]),
        check("POST /formation/optimize", lambda: request_json(api_url, "POST", "/formation/optimize", optimizer_payload)["best_formation"]),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
