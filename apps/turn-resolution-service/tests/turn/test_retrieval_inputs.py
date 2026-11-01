"""Unit tests for app/turn/retrieval_inputs.py."""

import uuid

import pytest
from app.config import settings
from app.models.memory import (
    MAX_ID_LIST_LENGTH,
    MAX_PARTICIPANT_NAME_CHARS,
    MAX_PARTICIPANT_NAMES,
)
from app.models.turn import LoadedState, RecentTurn, TurnRequest
from app.turn.retrieval_inputs import (
    build_active_conditional_fact_ids,
    build_retrieve_request,
    build_revealed_fact_ids,
    build_scene_entity_ids,
    cap_participant_names,
)

ALARM_ON = {"field": "flags.alarm", "op": "==", "value": True}


def test_conditional_fact_is_active_only_when_its_expression_holds() -> None:
    active_id, inactive_id, plain_id = (uuid.uuid4() for _ in range(3))
    snapshot = {
        "facts": [
            {"fact_id": str(active_id), "text": "t", "when_active": ALARM_ON},
            {
                "fact_id": str(inactive_id),
                "text": "t",
                "when_active": {"field": "flags.alarm", "op": "==", "value": False},
            },
            {"fact_id": str(plain_id), "text": "t"},
        ]
    }

    result = build_active_conditional_fact_ids(snapshot, {"flags": {"alarm": True}})

    assert result == [active_id]


@pytest.mark.parametrize(
    "expression",
    [
        {"field": "a", "op": "==", "value": 1, "AND": {}, "OR": {}},
        {"AND": "not-an-object"},
        {"field": "a", "op": "matches", "value": "("},
        {"field": "a", "op": "no_such_op", "value": 1},
    ],
)
def test_malformed_expression_fails_closed_without_raising(
    expression: dict[str, object],
) -> None:
    fact_id = uuid.uuid4()
    snapshot = {"facts": [{"fact_id": str(fact_id), "when_active": expression}]}

    assert build_active_conditional_fact_ids(snapshot, {"a": "x"}) == []


def test_one_bad_expression_does_not_hide_the_good_ones() -> None:
    bad_id, good_id = uuid.uuid4(), uuid.uuid4()
    snapshot = {
        "facts": [
            {"fact_id": str(bad_id), "when_active": {"AND": "x"}},
            {"fact_id": str(good_id), "when_active": ALARM_ON},
        ]
    }

    assert build_active_conditional_fact_ids(snapshot, {"flags": {"alarm": True}}) == [
        good_id
    ]


def test_facts_without_a_valid_id_or_expression_are_ignored() -> None:
    snapshot = {
        "facts": [
            "not a dict",
            {"fact_id": "not-a-uuid", "when_active": ALARM_ON},
            {"when_active": ALARM_ON},
            {"fact_id": str(uuid.uuid4()), "when_active": "string"},
        ]
    }

    assert build_active_conditional_fact_ids(snapshot, {"flags": {"alarm": True}}) == []
    assert build_active_conditional_fact_ids({}, {}) == []


def test_revealed_fact_ids_are_parsed_and_invalid_entries_dropped() -> None:
    fact_id = uuid.uuid4()

    assert build_revealed_fact_ids(
        {"revealed_facts": [str(fact_id), "nope", 7, None]}
    ) == [fact_id]
    assert build_revealed_fact_ids({}) == []
    assert build_revealed_fact_ids({"revealed_facts": "oops"}) == []


def test_revealed_fact_ids_are_capped_to_the_wire_limit() -> None:
    ids = [str(uuid.uuid4()) for _ in range(MAX_ID_LIST_LENGTH + 5)]

    assert len(build_revealed_fact_ids({"revealed_facts": ids})) == MAX_ID_LIST_LENGTH


def test_scene_ids_come_from_state_in_master_mode_only() -> None:
    tavern = uuid.uuid4()
    state = {"current_location_id": str(tavern)}
    entities = [{"entity_id": str(tavern)}]

    master = build_scene_entity_ids(state, {"mode": "master", "entities": entities})
    newbie = build_scene_entity_ids(state, {"mode": "newbie", "entities": entities})

    assert master == [tavern]
    assert newbie == []


def test_participant_names_are_capped_in_count_and_length() -> None:
    names = {uuid.uuid4(): "x" * 500 for _ in range(MAX_PARTICIPANT_NAMES + 3)}

    capped = cap_participant_names(names)

    assert len(capped) == MAX_PARTICIPANT_NAMES
    assert all(len(value) == MAX_PARTICIPANT_NAME_CHARS for value in capped.values())


def test_request_carries_every_eligibility_input_and_the_window() -> None:
    playthrough_id, participant_id = uuid.uuid4(), uuid.uuid4()
    tavern, fact_id, revealed_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    turn_request = TurnRequest(
        playthrough_id=playthrough_id,
        participant_id=participant_id,
        client_action_id=uuid.uuid4(),
        action_text="I ask about the key",
        action_mode="say",
        turn_count=4,
    )
    loaded_state = LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={
            "mode": "master",
            "entities": [{"entity_id": str(tavern)}],
            "facts": [{"fact_id": str(fact_id), "text": "t", "when_active": ALARM_ON}],
        },
        state={
            "current_location_id": str(tavern),
            "flags": {"alarm": True},
            "revealed_facts": [str(revealed_id)],
        },
        turn_count=4,
        checkpoint=None,
    )
    recent = [
        RecentTurn(
            turn_number=4,
            participant_id=participant_id,
            action_mode="say",
            action_text="Where is it?",
            narration_text="Nobody answers.",
        )
    ]

    request = build_retrieve_request(
        turn_request, loaded_state, recent, {participant_id: "Alice"}
    )

    assert request.playthrough_id == playthrough_id
    assert request.sequence == 4
    assert request.action_mode == "say"
    assert request.actor_participant_id == participant_id
    assert request.scene_authored_entity_ids == [tavern]
    assert request.active_conditional_fact_ids == [fact_id]
    assert request.revealed_fact_ids == [revealed_id]
    assert request.interlocutor_authored_entity_id is None
    assert request.last_actor_utterance == "Where is it?"
    assert request.recent_text == "Player: Where is it?\nNarrator: Nobody answers."
    assert request.recent_window_turns == settings.recent_window_turns
    assert request.participant_names == {participant_id: "Alice"}
