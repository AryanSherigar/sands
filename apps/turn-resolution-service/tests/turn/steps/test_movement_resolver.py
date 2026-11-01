"""Unit tests for movement_resolver.py."""

import pytest
from app.turn.steps import movement_resolver

CORRIDOR = "loc-corridor"
APPROACH = "loc-approach"
CABIN = "loc-cabin"
LOBBY = "loc-lobby"


def _location(
    entity_id: str, name: str, aliases: list[str], movement_class: str | None = None
) -> dict[str, object]:
    attributes = (
        {"movement_class": {"type": "enum", "initial": movement_class}}
        if movement_class
        else {}
    )
    return {
        "entity_id": entity_id,
        "entity_type": "location",
        "canonical_name": name,
        "aliases": aliases,
        "attributes_schema": attributes,
    }


SNAPSHOT: dict[str, object] = {
    "maps": [{"map_id": "m1"}],
    "entities": [
        _location(CORRIDOR, "East corridor", []),
        _location(
            APPROACH, "The last five metres", ["Cabin 14", "the cabin"], "approach"
        ),
        _location(CABIN, "Cabin 14", ["the cabin"], "interior"),
        _location(LOBBY, "Elevator lobby", ["the lobby"]),
        {"entity_id": "item-1", "entity_type": "item", "canonical_name": "Brass key"},
    ],
}


def _state(location: str = CORRIDOR) -> dict[str, object]:
    return {
        "current_location_id": location,
        "discovered_location_ids": [location],
        "_last_changed_fields": ["sanity"],
    }


def _resolve(text: str, mode: str = "do", location: str = CORRIDOR):
    return movement_resolver.resolve_movement(text, mode, _state(location), SNAPSHOT)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Go to Cabin 14", APPROACH),
        ("I walk toward cabin 14", APPROACH),
        ("approach Cabin 14", APPROACH),
        ("I head to the lobby", LOBBY),
        ("Enter Cabin 14", CABIN),
        ("go inside the cabin", CABIN),
        ("step into Cabin 14", CABIN),
        ("I go to the cabin", APPROACH),
    ],
)
def test_verb_and_place_pick_the_destination(text: str, expected: str) -> None:
    assert _resolve(text).destination_id == expected


def test_last_mentioned_place_wins() -> None:
    assert _resolve("go to the lobby then go to Cabin 14").destination_id == APPROACH


def test_negation_cancels_the_move() -> None:
    assert _resolve("I do not go to Cabin 14").destination_id is None
    assert _resolve("never approach Cabin 14").destination_id is None


def test_negation_in_an_earlier_clause_does_not_cancel() -> None:
    result = _resolve("I don't go to Cabin 14, I go to the lobby")

    assert result.destination_id == LOBBY


@pytest.mark.parametrize("mode", ["say", "story", "see"])
def test_only_do_actions_move_the_player(mode: str) -> None:
    result = _resolve("Go to Cabin 14", mode=mode)

    assert result.destination_id is None
    assert result.state == _state()


def test_place_without_a_movement_verb_does_nothing() -> None:
    assert _resolve("I look at Cabin 14").destination_id is None


def test_unknown_place_does_nothing() -> None:
    assert _resolve("go to the roof").destination_id is None


def test_item_names_are_not_places() -> None:
    assert _resolve("go to the Brass key").destination_id is None


def test_moving_to_the_current_location_does_nothing() -> None:
    assert _resolve("go to Cabin 14", location=APPROACH).destination_id is None


def test_move_updates_location_discovery_and_change_tracking() -> None:
    result = _resolve("Go to Cabin 14")

    assert result.state["current_location_id"] == APPROACH
    assert result.state["discovered_location_ids"] == [CORRIDOR, APPROACH]
    assert result.mutated_paths == {"current_location_id", "discovered_location_ids"}
    assert "current_location_id" in result.state["_last_changed_fields"]


def test_already_discovered_location_is_not_added_twice() -> None:
    state = _state()
    state["discovered_location_ids"] = [CORRIDOR, LOBBY]

    result = movement_resolver.resolve_movement(
        "go to the lobby", "do", state, SNAPSHOT
    )

    assert result.state["discovered_location_ids"] == [CORRIDOR, LOBBY]
    assert result.mutated_paths == {"current_location_id"}


def test_empty_change_list_stays_empty_so_all_conditions_run() -> None:
    state = _state()
    state["_last_changed_fields"] = []

    result = movement_resolver.resolve_movement(
        "go to the lobby", "do", state, SNAPSHOT
    )

    assert result.state["_last_changed_fields"] == []


def test_scenario_without_maps_never_moves() -> None:
    snapshot = {**SNAPSHOT, "maps": []}

    result = movement_resolver.resolve_movement(
        "go to Cabin 14", "do", _state(), snapshot
    )

    assert result.destination_id is None


def test_enforce_code_movement_overrides_a_model_proposal() -> None:
    working_state = {"current_location_id": LOBBY}

    movement_resolver.enforce_code_movement(working_state, APPROACH)

    assert working_state["current_location_id"] == APPROACH


def test_enforce_code_movement_leaves_model_move_when_code_found_none() -> None:
    working_state = {"current_location_id": LOBBY}

    movement_resolver.enforce_code_movement(working_state, None)

    assert working_state["current_location_id"] == LOBBY


def test_source_is_code_model_or_none() -> None:
    assert movement_resolver.log_movement_source(APPROACH, []) == "code"
    assert (
        movement_resolver.log_movement_source(None, ["current_location_id"]) == "model"
    )
    assert movement_resolver.log_movement_source(None, ["sanity"]) == "none"
