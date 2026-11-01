"""Authored encounter and outcome selection stay deterministic and private."""

import pytest
from app.combat.encounters import CombatEncounter, choose_outcome, prepare_encounter
from pydantic import ValidationError


def encounter():
    stats = {
        "max_health": 20,
        "health": 20,
        "attack": 9,
        "armor": 4,
        "speed": 5,
        "accuracy": 100,
        "luck": 40,
    }
    return {
        "encounter_id": "ambush",
        "start_condition": {"field": "location", "op": "==", "value": "road"},
        "player": {"actor_id": "hero", "side": "player", **stats},
        "opponent": {"actor_id": "bandit", "side": "opponent", **stats},
        "outcomes": [
            {"id": "rescue", "kind": "recover", "health": 5},
            {"id": "defeat", "kind": "end", "ending_id": "lost"},
        ],
        "fallback_outcome_id": "rescue",
    }


def test_start_uses_authored_stats_but_current_player_health():
    config = CombatEncounter.model_validate(encounter())
    state = prepare_encounter(config, {"location": "road", "player": {"health": 8}})
    assert state.encounter_id == "ambush"
    assert (
        next(actor.health for actor in state.combatants if actor.side == "player") == 8
    )


def test_start_requires_condition_and_valid_health():
    config = CombatEncounter.model_validate(encounter())
    for state in (
        {"location": "inn", "player": {"health": 8}},
        {"location": "road", "player": {"health": 0}},
        {"location": "road", "player": {"health": 21}},
    ):
        with pytest.raises(ValueError):
            prepare_encounter(config, state)


def test_only_eligible_authored_decisions_or_valid_fallback():
    data = encounter()
    data["outcomes"][1]["condition"] = {"field": "can_end", "op": "==", "value": True}
    config = CombatEncounter.model_validate(data)
    assert choose_outcome(config, {"can_end": True}, "defeat").id == "defeat"
    assert choose_outcome(config, {"can_end": False}, "defeat").id == "rescue"
    assert choose_outcome(config, {}, "invented").id == "rescue"


def test_invalid_or_ineligible_fallback_fails_closed():
    data = encounter()
    data["fallback_outcome_id"] = "missing"
    with pytest.raises(ValidationError):
        CombatEncounter.model_validate(data)
    data = encounter()
    data["outcomes"][0]["condition"] = {"field": "safe", "op": "==", "value": True}
    with pytest.raises(ValueError):
        choose_outcome(CombatEncounter.model_validate(data), {}, None)


def test_outcome_shapes_and_unique_ids_are_validated():
    data = encounter()
    data["outcomes"][1]["id"] = "rescue"
    with pytest.raises(ValidationError):
        CombatEncounter.model_validate(data)
    data = encounter()
    data["outcomes"][0]["health"] = 0
    with pytest.raises(ValidationError):
        CombatEncounter.model_validate(data)
