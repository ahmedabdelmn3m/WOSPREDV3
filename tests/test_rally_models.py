"""Validation tests for the complete rally-evaluation request model."""

import pytest
from pydantic import ValidationError

from api.rally_models import RallyEvaluationRequest, RallyPlanOptimizationRequest


def valid_payload() -> dict:
    return {
        "objective": "MAX_DAMAGE",
        "leaderHeroes": [
            {"heroId": "jeronimo", "widgetLevel": 10},
            {"heroId": "molly", "widgetLevel": 5},
            {"heroId": "zinman", "widgetLevel": 0},
        ],
        "joinerHeroIds": ["jessie", "jessie", "jessie", "jessie"],
        "troopType": "infantry",
    }


@pytest.mark.parametrize(
    "leaders",
    [
        [
            {"heroId": "jeronimo", "widgetLevel": 0},
            {"heroId": "molly", "widgetLevel": 0},
        ],
        [
            {"heroId": "jeronimo", "widgetLevel": 0},
            {"heroId": "molly", "widgetLevel": 0},
            {"heroId": "zinman", "widgetLevel": 0},
            {"heroId": "logan", "widgetLevel": 0},
        ],
    ],
)
def test_requires_exactly_three_leader_heroes(leaders):
    payload = valid_payload()
    payload["leaderHeroes"] = leaders
    with pytest.raises(ValidationError):
        RallyEvaluationRequest.model_validate(payload)


@pytest.mark.parametrize(
    "joiners",
    [
        ["jessie", "jasser", "seo-yoon"],
        ["jessie", "jasser", "seo-yoon", "sergey", "ling"],
    ],
)
def test_requires_exactly_four_joiner_heroes(joiners):
    payload = valid_payload()
    payload["joinerHeroIds"] = joiners
    with pytest.raises(ValidationError):
        RallyEvaluationRequest.model_validate(payload)


def test_requires_one_leader_of_each_troop_type():
    payload = valid_payload()
    payload["leaderHeroes"] = [
        {"heroId": "jeronimo", "widgetLevel": 0},
        {"heroId": "logan", "widgetLevel": 0},
        {"heroId": "molly", "widgetLevel": 0},
    ]
    with pytest.raises(ValidationError, match="exactly one infantry"):
        RallyEvaluationRequest.model_validate(payload)


@pytest.mark.parametrize("widget_level", [-1, 11])
def test_widget_level_must_be_between_zero_and_ten(widget_level):
    payload = valid_payload()
    payload["leaderHeroes"][0]["widgetLevel"] = widget_level
    with pytest.raises(ValidationError):
        RallyEvaluationRequest.model_validate(payload)


def test_joiner_duplicates_are_allowed_but_unknown_joiners_are_rejected():
    request = RallyEvaluationRequest.model_validate(valid_payload())
    assert request.joiner_hero_ids == ["jessie"] * 4

    payload = valid_payload()
    payload["joinerHeroIds"][3] = "not-a-hero"
    with pytest.raises(ValidationError, match="Unknown joiner hero ID"):
        RallyEvaluationRequest.model_validate(payload)


def test_duplicate_leader_ids_are_rejected():
    payload = valid_payload()
    payload["leaderHeroes"] = [
        {"heroId": "jeronimo", "widgetLevel": 0},
        {"heroId": "jeronimo", "widgetLevel": 5},
        {"heroId": "zinman", "widgetLevel": 10},
    ]
    with pytest.raises(ValidationError, match="must be unique"):
        RallyEvaluationRequest.model_validate(payload)


def test_gwen_disputed_flag_and_nested_models_serialize_correctly():
    payload = valid_payload()
    payload["leaderHeroes"] = [
        {"heroId": "hector", "widgetLevel": 8},
        {"heroId": "norah", "widgetLevel": 9},
        {"heroId": "gwen", "widgetLevel": 10},
    ]

    default_request = RallyEvaluationRequest.model_validate(payload)
    assert default_request.model_dump(by_alias=True)["includeDisputedSkills"] is False
    assert default_request.to_service_kwargs()["include_disputed_skills"] is False

    payload["includeDisputedSkills"] = True
    request = RallyEvaluationRequest.model_validate(payload)
    serialized = request.model_dump(by_alias=True)
    service_kwargs = request.to_service_kwargs()

    assert serialized["leaderHeroes"][2] == {"heroId": "gwen", "widgetLevel": 10}
    assert serialized["includeDisputedSkills"] is True
    assert service_kwargs["leader_heroes"][2] == {"hero_id": "gwen", "widget_level": 10}
    assert service_kwargs["include_disputed_skills"] is True


def test_plan_optimizer_request_preserves_candidate_priority_and_complete_leader_inputs():
    rally = valid_payload()
    rally.pop("joinerHeroIds")
    rally["rallyId"] = "castle-holder"
    rally["priorityWeight"] = 1.2
    request = RallyPlanOptimizationRequest.model_validate({
        "rallies": [rally],
        "availableHeroIds": ["jessie", "jasser", "lumak", "ling"],
        "availableHeroCounts": {"jessie": 1, "jasser": 1, "lumak": 1, "ling": 1},
    })

    service_kwargs = request.to_service_kwargs()
    assert service_kwargs["available_hero_ids"] == ["jessie", "jasser", "lumak", "ling"]
    assert service_kwargs["rallies"][0]["rally_id"] == "castle-holder"
    assert service_kwargs["rallies"][0]["priority_weight"] == 1.2
    assert len(service_kwargs["rallies"][0]["leader_heroes"]) == 3


def test_plan_optimizer_request_rejects_duplicate_or_negative_inventory():
    rally = valid_payload()
    rally.pop("joinerHeroIds")
    rally["rallyId"] = "rally-1"

    with pytest.raises(ValidationError, match="must be unique"):
        RallyPlanOptimizationRequest.model_validate({
            "rallies": [rally],
            "availableHeroIds": ["jessie", "jessie"],
        })
    with pytest.raises(ValidationError, match="cannot be negative"):
        RallyPlanOptimizationRequest.model_validate({
            "rallies": [rally],
            "availableHeroIds": ["jessie"],
            "availableHeroCounts": {"jessie": -1},
        })
