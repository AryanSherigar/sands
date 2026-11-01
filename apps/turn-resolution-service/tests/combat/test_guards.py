"""Narrative turns and generic state changes cannot control combat."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.exceptions.combat_exceptions import CombatActionError
from app.models.auth import CurrentUser
from app.models.tool_call import ProposedMutation
from app.models.turn import TurnRequestInput
from app.turn.state_visibility import visible_state
from app.turn.steps.request_receiver import receive_request
from app.turn.steps.state_validator import validate_applied_change, validate_mutation


def test_combat_state_is_not_exposed_through_generic_state():
    assert visible_state(
        {"_combat": {"secret": "weakness"}, "_combat_history": ["secret"], "clock": 1},
        {},
    ) == {"clock": 1}


def test_generic_mutations_and_conditions_cannot_change_combat():
    before = {"_combat": {"status": "active", "revision": 1}}
    mutation = ProposedMutation(
        tool_name="set_field", op="set", path="_combat.revision", value=2
    )
    assert not validate_mutation(mutation, before, {}).is_valid
    after = {"_combat": {"status": "active", "revision": 2}}
    assert not validate_applied_change(
        "_combat", after, {}, original_state=before
    ).is_valid
    after = {**before, "_combat_history": ["ambush"]}
    assert not validate_applied_change(
        "_combat_history", after, {}, original_state=before
    ).is_valid


def test_generic_mutations_cannot_change_player_health_during_combat():
    before = {"_combat": {"status": "active"}, "player": {"health": 10}}
    mutation = ProposedMutation(
        tool_name="set_field", op="set", path="player", value={"health": 20}
    )
    schema = {
        "state_schema": {
            "player": {"type": "object", "fields": {"health": {"type": "number"}}}
        }
    }
    assert not validate_mutation(mutation, before, schema).is_valid
    after = {**before, "player": {"health": 20}}
    assert not validate_applied_change(
        "player", after, schema, original_state=before
    ).is_valid


async def test_narrative_turn_is_blocked_while_combat_active():
    playthrough_id, participant_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    playthrough_repo, participant_repo = AsyncMock(), AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0, state={"_combat": {"status": "active"}}
    )
    participant_repo.list_by_playthrough.return_value = [
        SimpleNamespace(
            participant_id=participant_id, user_id=user_id, turn_order_position=1
        )
    ]
    request = TurnRequestInput(
        playthrough_id=playthrough_id,
        participant_id=participant_id,
        client_action_id=uuid.uuid4(),
        action_text="I wait.",
    )
    with pytest.raises(CombatActionError):
        await receive_request(
            request,
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )


async def test_player_defeat_waits_for_an_authored_outcome():
    playthrough_id, participant_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    playthrough_repo, participant_repo = AsyncMock(), AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=1, state={"_combat": {"status": "player_defeated"}}
    )
    participant_repo.list_by_playthrough.return_value = [
        SimpleNamespace(
            participant_id=participant_id, user_id=user_id, turn_order_position=1
        )
    ]
    request = TurnRequestInput(
        playthrough_id=playthrough_id,
        participant_id=participant_id,
        client_action_id=uuid.uuid4(),
        action_text="I wait.",
    )
    with pytest.raises(CombatActionError):
        await receive_request(
            request,
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )


async def test_recovered_player_can_continue_the_story():
    playthrough_id, participant_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    playthrough_repo, participant_repo = AsyncMock(), AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active",
        turn_count=3,
        state={"_combat": {"status": "player_defeated", "outcome_id": "rescue"}},
    )
    participant_repo.list_by_playthrough.return_value = [
        SimpleNamespace(
            participant_id=participant_id, user_id=user_id, turn_order_position=1
        )
    ]
    request = TurnRequestInput(
        playthrough_id=playthrough_id,
        participant_id=participant_id,
        client_action_id=uuid.uuid4(),
        action_text="I recover.",
    )
    result = await receive_request(
        request,
        playthrough_repo,
        participant_repo,
        CurrentUser(user_id=user_id, token_version=1),
    )
    assert result.action_text == "I recover."


async def test_post_turn_notification_uses_narrative_count(monkeypatch):
    from app.models.turn import LoadedState, TurnRequest
    from app.turn import pipeline

    notify = AsyncMock()
    monkeypatch.setattr(pipeline, "_notify_next_participant", notify)
    monkeypatch.setattr(pipeline.spectator_manager, "publish", AsyncMock())
    playthrough_id, participant_id = uuid.uuid4(), uuid.uuid4()
    request = TurnRequest(
        playthrough_id=playthrough_id,
        participant_id=participant_id,
        client_action_id=uuid.uuid4(),
        action_text="Wait",
        turn_count=6,
    )
    loaded = LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={},
        state={},
        turn_count=6,
        narrative_turn_count=1,
        checkpoint=None,
    )
    await pipeline._after_write(request, loaded, [], False)
    notify.assert_awaited_once_with(playthrough_id, 2, [])
