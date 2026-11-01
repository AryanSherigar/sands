"""Fantasy exchanges through the real turn transaction with a fake narrator."""

import uuid

import pytest
from app.exceptions.fantasy_exceptions import (
    FantasyActionError,
    FantasyReplayConflictError,
)
from app.turn.steps import ai_orchestrator
from pipeline_seed import narrator, seed_master_playthrough, stored_state, take_turn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _snapshot():
    return {
        "mode": "master",
        "enabled_tools": ["status_hud"],
        "world_data": {},
        "fantasy_mechanics": {
            "version": 1,
            "profile": "zegaris",
            "energy_max": 100,
            "initial_energy": 60,
            "rest_cost": 5,
            "bounty_reward": 8,
            "locations": {
                "inn": "inn",
                "quest_giver": "hall",
                "recovery": "shaft",
                "cremation": "pyre",
            },
            "corpse_item_id": "body",
        },
        "state_schema": {
            "player": {
                "type": "object",
                "fields": {
                    "coins": {"type": "number"},
                    "energy": {"type": "number"},
                    "inventory": {"type": "list"},
                },
            },
            "quests": {
                "type": "object",
                "fields": {
                    "retrieval": {
                        "type": "object",
                        "fields": {"stage": {"type": "string"}},
                    }
                },
            },
        },
        "entities": [],
        "rule_invariants": [],
        "end_conditions": [],
        "scenario_conditions": [],
    }


async def _setup(session, monkeypatch, coins=10):
    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_with_tools", narrator("You rest.")
    )
    return await seed_master_playthrough(
        session,
        _snapshot(),
        {
            "player": {"coins": coins, "energy": 25, "inventory": []},
            "quests": {"retrieval": {"stage": "offered"}},
            "current_location_id": "inn",
            "narrative": {},
        },
    )


async def test_rest_persists_once_and_replays_same_id(
    db_session: AsyncSession, monkeypatch
):
    playthrough, participant = await _setup(db_session, monkeypatch)
    request_id = uuid.uuid4()
    fields = {"action_kind": "fantasy_action", "fantasy_action": {"action_id": "rest"}}
    first = await take_turn(
        db_session, playthrough, participant, client_action_id=request_id, **fields
    )
    replay = await take_turn(
        db_session, playthrough, participant, client_action_id=request_id, **fields
    )
    state = await stored_state(db_session, playthrough)
    assert state["player"]["coins"] == 5
    assert state["player"]["energy"] == 100
    assert first[-1].event == replay[-1].event == "done"
    assert playthrough.turn_count == 1
    with pytest.raises(FantasyReplayConflictError):
        await take_turn(
            db_session,
            playthrough,
            participant,
            client_action_id=request_id,
            action_kind="fantasy_action",
            fantasy_action={"action_id": "claim_retrieval_reward"},
        )


async def test_insufficient_coins_do_not_persist(db_session: AsyncSession, monkeypatch):
    playthrough, participant = await _setup(db_session, monkeypatch, coins=4)
    with pytest.raises(FantasyActionError):
        await take_turn(
            db_session,
            playthrough,
            participant,
            action_kind="fantasy_action",
            fantasy_action={"action_id": "rest"},
        )
    state = await stored_state(db_session, playthrough)
    assert state["player"]["coins"] == 4
    assert state["player"]["energy"] == 25
    assert playthrough.turn_count == 0


async def test_reward_can_only_be_claimed_once(db_session: AsyncSession, monkeypatch):
    playthrough, participant = await _setup(db_session, monkeypatch)
    playthrough.state = {
        **playthrough.state,
        "current_location_id": "hall",
        "quests": {"retrieval": {"stage": "cremated"}},
    }
    await db_session.flush()
    fields = {
        "action_kind": "fantasy_action",
        "fantasy_action": {"action_id": "claim_retrieval_reward"},
    }
    await take_turn(db_session, playthrough, participant, **fields)
    with pytest.raises(FantasyActionError):
        await take_turn(db_session, playthrough, participant, **fields)
    state = await stored_state(db_session, playthrough)
    assert state["player"]["coins"] == 18
    assert state["quests"]["retrieval"]["stage"] == "rewarded"
    assert playthrough.turn_count == 1
