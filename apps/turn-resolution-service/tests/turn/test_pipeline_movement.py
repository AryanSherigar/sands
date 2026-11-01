"""A typed move changes location in code, so a location-gated rule fires in
the same turn rather than waiting for the narrator to call set_field."""

import uuid

import pytest
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.turn.steps import ai_orchestrator
from pipeline_seed import narrator, seed_master_playthrough, stored_state, take_turn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

CORRIDOR_ID = str(uuid.uuid4())
APPROACH_ID = str(uuid.uuid4())
CABIN_ID = str(uuid.uuid4())
START_SANITY = 20
CARDINAL_COST = 10


def _location(
    entity_id: str, name: str, aliases: list[str], movement_class: str | None
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
        "description": None,
        "attributes_schema": attributes,
        "obtainable": None,
        "narrator_instruction": None,
        "is_player": False,
    }


def _r4_condition() -> dict[str, object]:
    return {
        "condition_id": "r4-approach",
        "label": "R4 approach",
        "is_one_shot": True,
        "condition_expression": {
            "field": "current_location_id",
            "op": "==",
            "value": APPROACH_ID,
            "AND": {
                "field": "cabin.lamp",
                "op": "==",
                "value": "on",
                "AND": {"field": "rule_status.r4", "op": "!=", "value": "violated"},
            },
        },
        "state_mutations": [
            {"path": "sanity", "op": "decrement", "value": CARDINAL_COST},
            {"path": "rule_status.r4", "op": "set", "value": "violated"},
        ],
    }


def _snapshot() -> dict[str, object]:
    return {
        "mode": "master",
        "narrator_persona": "Dry.",
        "world_data": {},
        "maps": [{"map_id": str(uuid.uuid4())}],
        "state_schema": {
            "current_location_id": {"type": "entity_ref", "entity_type": "location"},
            "discovered_location_ids": {"type": "list", "item_type": "entity_ref"},
            "sanity": {"type": "number", "initial": START_SANITY, "min": 0},
            "cabin": {"type": "object", "fields": {"lamp": {"type": "string"}}},
            "rule_status": {"type": "object", "fields": {"r4": {"type": "string"}}},
        },
        "entities": [
            _location(CORRIDOR_ID, "East corridor", [], None),
            _location(APPROACH_ID, "The last five metres", ["Cabin 14"], "approach"),
            _location(CABIN_ID, "Cabin 14", ["Cabin 14"], "interior"),
        ],
        "rule_invariants": [],
        "end_conditions": [],
        "scenario_minigames": [],
        "scenario_conditions": [_r4_condition()],
    }


def _state(lamp: str) -> dict[str, object]:
    return {
        "current_location_id": CORRIDOR_ID,
        "discovered_location_ids": [CORRIDOR_ID],
        "sanity": START_SANITY,
        "cabin": {"lamp": lamp},
        "rule_status": {"r4": "intact"},
        "_last_changed_fields": ["sanity"],
        "narrative": {},
    }


async def _seed(session: AsyncSession, lamp: str) -> tuple[Playthrough, Participant]:
    return await seed_master_playthrough(session, _snapshot(), _state(lamp))


async def test_approaching_with_the_lamp_on_violates_r4_in_the_same_turn(
    db_session: AsyncSession, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session, "on")
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("You walk on.")
    )

    await take_turn(db_session, playthrough, participant, action_text="Go to Cabin 14")
    state = await stored_state(db_session, playthrough)

    assert state["current_location_id"] == APPROACH_ID
    assert state["discovered_location_ids"] == [CORRIDOR_ID, APPROACH_ID]
    assert state["rule_status"]["r4"] == "violated"
    assert state["sanity"] == START_SANITY - CARDINAL_COST


async def test_approaching_with_the_lamp_off_does_not_violate_r4(
    db_session: AsyncSession, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session, "off")
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("You walk on.")
    )

    await take_turn(db_session, playthrough, participant, action_text="Go to Cabin 14")
    state = await stored_state(db_session, playthrough)

    assert state["current_location_id"] == APPROACH_ID
    assert state["rule_status"]["r4"] == "intact"


async def test_entering_moves_inside_rather_than_to_the_approach(
    db_session: AsyncSession, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session, "off")
    monkeypatch.setattr(
        ai_orchestrator.narration_router,
        "stream_with_tools",
        narrator("The door gives."),
    )

    await take_turn(db_session, playthrough, participant, action_text="Enter Cabin 14")
    state = await stored_state(db_session, playthrough)

    assert state["current_location_id"] == CABIN_ID


async def test_saying_the_place_name_does_not_move_the_player(
    db_session: AsyncSession, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session, "on")
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("Silence.")
    )

    await take_turn(
        db_session,
        playthrough,
        participant,
        action_text="Go to Cabin 14",
        action_mode="say",
    )
    state = await stored_state(db_session, playthrough)

    assert state["current_location_id"] == CORRIDOR_ID
