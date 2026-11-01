"""Provider-free combat lifecycle against the real test database."""

import asyncio
import copy
import uuid

import pytest
from app.db.models.playthrough import Playthrough
from app.main import app
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.combat import CombatStartRequest
from app.services.combat_lifecycle_service import execute_lifecycle
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_encounters import encounter
from test_persistence import seed

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def configure(session):
    ids = await seed(session)
    row = await session.get(Playthrough, ids[0])
    config = encounter()
    config["opponent"]["speed"] = 10
    config["opponent"]["attack"] = 30
    row.scenario_snapshot = {
        "mode": "master",
        "fantasy_combat": {"encounters": [config]},
        "state_schema": {
            "player": {
                "type": "object",
                "fields": {"health": {"type": "number", "min": 0, "max": 20}},
            }
        },
        "end_conditions": [],
        "entities": [],
    }
    row.state = {"location": "road", "player": {"health": 8}}
    await session.commit()
    return ids


def request(ids, **extra):
    return {
        "playthrough_id": str(ids[0]),
        "participant_id": str(ids[1]),
        "client_action_id": str(uuid.uuid4()),
        **extra,
    }


async def test_start_attack_and_recovery_are_atomic_and_replayable(
    db_session, async_client
):
    ids = await configure(db_session)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=ids[2], token_version=1
    )
    try:
        start = request(ids, encounter_id="ambush")
        first = await async_client.post("/v1/combat/start", json=start)
        assert first.status_code == 200, first.text
        assert first.json()["current_actor_id"] == "bandit"
        assert (
            await async_client.post("/v1/combat/start", json=start)
        ).json() == first.json()
        action = {
            "playthrough_id": str(ids[0]),
            "participant_id": str(ids[1]),
            "action": {
                "client_action_id": str(uuid.uuid4()),
                "expected_revision": 0,
                "actor_id": "bandit",
                "target_id": "hero",
                "action_id": "attack",
            },
        }
        hit = await async_client.post("/v1/combat/action", json=action)
        assert hit.status_code == 200, hit.text
        assert hit.json()["state"]["status"] == "player_defeated"
        await db_session.refresh(await db_session.get(Playthrough, ids[0]))
        row = await db_session.get(Playthrough, ids[0])
        assert row.state["player"]["health"] == 0 and row.status == "active"
        outcome = request(ids, expected_revision=1)
        resolved = await async_client.post("/v1/combat/outcome", json=outcome)
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["outcome_id"] == "rescue"
        assert (
            await async_client.post("/v1/combat/outcome", json=outcome)
        ).json() == resolved.json()
        await db_session.refresh(row)
        assert row.state["player"]["health"] == 5 and row.status == "active"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_start_rejects_unavailable_and_unowned_encounters(
    db_session, async_client
):
    ids = await configure(db_session)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=ids[2], token_version=1
    )
    try:
        assert (
            await async_client.post(
                "/v1/combat/start", json=request(ids, encounter_id="unknown")
            )
        ).status_code == 409
        row = await db_session.get(Playthrough, ids[0])
        row.state = {"location": "inn", "player": {"health": 8}}
        await db_session.commit()
        assert (
            await async_client.post(
                "/v1/combat/start", json=request(ids, encounter_id="ambush")
            )
        ).status_code == 409
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            user_id=uuid.uuid4(), token_version=1
        )
        assert (
            await async_client.post(
                "/v1/combat/start", json=request(ids, encounter_id="ambush")
            )
        ).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_options_exposes_only_eligible_encounters_and_current_state(
    db_session, async_client
):
    ids = await configure(db_session)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=ids[2], token_version=1
    )
    try:
        url = f"/v1/combat/{ids[0]}/options?participant_id={ids[1]}"
        response = await async_client.get(url)
        assert response.status_code == 200
        assert response.json() == {
            "state": None,
            "encounters": [{"encounter_id": "ambush", "title": "Encounter"}],
        }
        await async_client.post(
            "/v1/combat/start", json=request(ids, encounter_id="ambush")
        )
        options = (await async_client.get(url)).json()
        assert options["state"]["status"] == "active" and options["encounters"] == []
        assert "luck" not in str(options)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def defeat_player(client, ids):
    start = await client.post(
        "/v1/combat/start", json=request(ids, encounter_id="ambush")
    )
    assert start.status_code == 200, start.text
    action = {
        "playthrough_id": str(ids[0]),
        "participant_id": str(ids[1]),
        "action": {
            "client_action_id": str(uuid.uuid4()),
            "expected_revision": 0,
            "actor_id": "bandit",
            "target_id": "hero",
            "action_id": "attack",
        },
    }
    result = await client.post("/v1/combat/action", json=action)
    assert result.status_code == 200, result.text


async def test_authored_defeat_ends_playthrough_and_retry_replays(
    db_session, async_client
):
    from app.db.models.memory_outbox import MemoryOutbox
    from sqlalchemy import select

    ids = await configure(db_session)
    row = await db_session.get(Playthrough, ids[0])
    snapshot = dict(row.scenario_snapshot)
    config = dict(snapshot["fantasy_combat"]["encounters"][0])
    ending_id = str(uuid.uuid4())
    config["outcomes"] = [{"id": "defeat", "kind": "end", "ending_id": ending_id}]
    config["fallback_outcome_id"] = "defeat"
    snapshot["fantasy_combat"] = {"encounters": [config]}
    snapshot["end_conditions"] = [
        {
            "end_condition_id": ending_id,
            "outcome_tag": "lose",
            "outcome_title": "Lost",
            "outcome_text": "The end.",
        }
    ]
    row.scenario_snapshot = snapshot
    row.memory_publish_revision = 1
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=ids[2], token_version=1
    )
    try:
        await defeat_player(async_client, ids)
        outcome = request(ids, expected_revision=1)
        result = await async_client.post("/v1/combat/outcome", json=outcome)
        assert result.status_code == 200, result.text
        await db_session.refresh(row)
        assert row.status == "completed" and str(row.ended_outcome_id) == ending_id
        rows = (
            (
                await db_session.execute(
                    select(MemoryOutbox).where(MemoryOutbox.playthrough_id == ids[0])
                )
            )
            .scalars()
            .all()
        )
        assert [item.item_kind for item in rows].count("flush") == 1
        assert [item.item_kind for item in rows].count("turn") == 3
        assert (
            await async_client.post("/v1/combat/outcome", json=outcome)
        ).json() == result.json()
        assert (
            await async_client.post(
                "/v1/combat/outcome", json={**outcome, "expected_revision": 99}
            )
        ).status_code == 409
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_ineligible_fallback_does_not_change_state(db_session, async_client):
    ids = await configure(db_session)
    row = await db_session.get(Playthrough, ids[0])
    snapshot = copy.deepcopy(row.scenario_snapshot)
    config = dict(snapshot["fantasy_combat"]["encounters"][0])
    config["outcomes"][0]["condition"] = {"field": "saved", "op": "==", "value": True}
    snapshot["fantasy_combat"] = {"encounters": [config]}
    row.scenario_snapshot = snapshot
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=ids[2], token_version=1
    )
    try:
        await defeat_player(async_client, ids)
        result = await async_client.post(
            "/v1/combat/outcome", json=request(ids, expected_revision=1)
        )
        assert result.status_code == 409
        await db_session.refresh(row)
        assert row.turn_count == 2 and row.state["player"]["health"] == 0
        assert row.state["_combat"]["outcome_id"] is None
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_concurrent_start_replays_once_and_stale_story_write_fails(db_session):
    from app.exceptions.turn_exceptions import OptimisticLockError
    from app.repositories.playthrough_repo import PlaythroughRepo

    ids = await configure(db_session)
    command = CombatStartRequest.model_validate(request(ids, encounter_id="ambush"))
    user = CurrentUser(user_id=ids[2], token_version=1)
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)

    async def execute():
        async with factory() as session:
            return await execute_lifecycle(session, command, user)

    first, second = await asyncio.gather(execute(), execute())
    assert first == second
    async with factory() as session:
        row = await session.get(Playthrough, ids[0])
        assert row.turn_count == 1 and row.state["_combat_history"] == ["ambush"]
        with pytest.raises(OptimisticLockError):
            await PlaythroughRepo(session).update_state(ids[0], {}, 1, 0)
        await session.rollback()


async def test_start_write_failure_rolls_back(db_session, monkeypatch):
    from app.repositories.turn_log_repo import TurnLogRepo

    ids = await configure(db_session)
    command = CombatStartRequest.model_validate(request(ids, encounter_id="ambush"))
    user = CurrentUser(user_id=ids[2], token_version=1)

    async def fail(*args, **kwargs):
        raise RuntimeError("write failed")

    monkeypatch.setattr(TurnLogRepo, "create", fail)
    with pytest.raises(RuntimeError, match="write failed"):
        await execute_lifecycle(db_session, command, user)
    row = await db_session.get(Playthrough, ids[0])
    assert row.turn_count == 0 and "_combat" not in row.state


async def test_start_lost_response_replays_after_commit(db_session, monkeypatch):
    ids = await configure(db_session)
    command = CombatStartRequest.model_validate(request(ids, encounter_id="ambush"))
    user = CurrentUser(user_id=ids[2], token_version=1)
    original_commit = db_session.commit

    async def commit_then_disconnect():
        await original_commit()
        raise asyncio.CancelledError()

    monkeypatch.setattr(db_session, "commit", commit_then_disconnect)
    with pytest.raises(asyncio.CancelledError):
        await execute_lifecycle(db_session, command, user)
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    async with factory() as fresh:
        replay = await execute_lifecycle(fresh, command, user)
        row = await fresh.get(Playthrough, ids[0])
        assert replay.revision == 0 and row.turn_count == 1


async def test_combat_events_do_not_consume_narrative_context_or_turn_order(db_session):
    from app.db.models.participant import Participant
    from app.db.models.user import User
    from app.models.turn import TurnRequestInput
    from app.repositories.participant_repo import ParticipantRepo
    from app.repositories.playthrough_repo import PlaythroughRepo
    from app.repositories.turn_log_repo import TurnLogRepo
    from app.turn.steps.request_receiver import receive_request

    ids = await configure(db_session)
    command = CombatStartRequest.model_validate(request(ids, encounter_id="ambush"))
    user = CurrentUser(user_id=ids[2], token_version=1)
    await execute_lifecycle(db_session, command, user)
    row = await db_session.get(Playthrough, ids[0])
    row.state = {
        **row.state,
        "_combat": {**row.state["_combat"], "status": "opponent_defeated"},
    }
    other_id = uuid.uuid4()
    db_session.add(
        User(user_id=other_id, display_name="Other", auth_provider_id=str(other_id))
    )
    await db_session.flush()
    db_session.add(
        Participant(
            playthrough_id=ids[0],
            user_id=other_id,
            role="joined",
            turn_order_position=2,
        )
    )
    await db_session.commit()
    logs = TurnLogRepo(db_session)
    assert await logs.count_combat_events(ids[0]) == 1
    assert await logs.list_recent(ids[0], 10) == []
    turn = TurnRequestInput(
        playthrough_id=ids[0],
        participant_id=ids[1],
        client_action_id=uuid.uuid4(),
        action_text="I continue.",
    )
    accepted = await receive_request(
        turn, PlaythroughRepo(db_session), ParticipantRepo(db_session), user
    )
    assert accepted.turn_count == 1


async def test_multiplayer_encounter_belongs_to_current_story_actor(db_session):
    from app.db.models.participant import Participant
    from app.db.models.user import User
    from app.exceptions.turn_exceptions import ParticipantAccessDeniedError
    from app.models.combat import CombatStartRequest
    from app.services.combat_service import apply_combat_action
    from test_persistence import attack

    ids = await configure(db_session)
    row = await db_session.get(Playthrough, ids[0])
    row.turn_count = 1
    joined_user_id, joined_id = uuid.uuid4(), uuid.uuid4()
    db_session.add(
        User(
            user_id=joined_user_id,
            display_name="Other",
            auth_provider_id=str(joined_user_id),
        )
    )
    await db_session.flush()
    db_session.add(
        Participant(
            participant_id=joined_id,
            playthrough_id=ids[0],
            user_id=joined_user_id,
            role="joined",
            turn_order_position=2,
        )
    )
    await db_session.commit()
    owner = CurrentUser(user_id=ids[2], token_version=1)
    joined = CurrentUser(user_id=joined_user_id, token_version=1)
    with pytest.raises(ParticipantAccessDeniedError):
        await execute_lifecycle(
            db_session,
            CombatStartRequest.model_validate(request(ids, encounter_id="ambush")),
            owner,
        )
    joined_ids = (ids[0], joined_id, joined_user_id)
    await execute_lifecycle(
        db_session,
        CombatStartRequest.model_validate(request(joined_ids, encounter_id="ambush")),
        joined,
    )
    with pytest.raises(ParticipantAccessDeniedError):
        await apply_combat_action(
            db_session, ids[0], ids[1], owner, attack(actor="bandit", target="hero")
        )
    result = await apply_combat_action(
        db_session, ids[0], joined_id, joined, attack(actor="bandit", target="hero")
    )
    assert result.state.status == "player_defeated"


async def test_recovery_changes_health_and_location_atomically(
    db_session, async_client
):
    ids = await configure(db_session)
    row = await db_session.get(Playthrough, ids[0])
    snapshot = copy.deepcopy(row.scenario_snapshot)
    location_id = str(uuid.uuid4())
    snapshot["fantasy_combat"]["encounters"][0]["outcomes"][0]["location_id"] = (
        location_id
    )
    snapshot["entities"] = [{"entity_id": location_id, "entity_type": "location"}]
    snapshot["state_schema"]["current_location_id"] = {"type": "entity_ref"}
    snapshot["state_schema"]["discovered_location_ids"] = {
        "type": "list",
        "item_type": "string",
    }
    snapshot["rule_invariants"] = [
        {
            "invariant_expression": {
                "field": "player.health",
                "op": "==",
                "value": 8,
                "OR": {
                    "field": "player.health",
                    "op": "==",
                    "value": 0,
                    "OR": {
                        "field": "current_location_id",
                        "op": "==",
                        "value": location_id,
                    },
                },
            }
        }
    ]
    row.scenario_snapshot = snapshot
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=ids[2], token_version=1
    )
    try:
        await defeat_player(async_client, ids)
        result = await async_client.post(
            "/v1/combat/outcome", json=request(ids, expected_revision=1)
        )
        assert result.status_code == 200, result.text
        await db_session.refresh(row)
        assert row.state["current_location_id"] == location_id
        assert row.state["player"]["health"] == 5
        assert location_id in row.state["discovered_location_ids"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
