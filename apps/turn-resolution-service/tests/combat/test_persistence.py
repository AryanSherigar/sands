"""Combat action atomicity against isolated PostgreSQL; no LLM required."""

import asyncio
import uuid

import pytest
from app.combat.models import CombatAction, Combatant
from app.combat.resolver import start_combat
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from app.exceptions.combat_exceptions import (
    CombatActionError,
    CombatReplayConflictError,
)
from app.exceptions.turn_exceptions import ParticipantAccessDeniedError
from app.models.auth import CurrentUser
from app.services.combat_service import apply_combat_action
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def seed(session):
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        User(user_id=user_id, display_name="Test", auth_provider_id=str(user_id))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=user_id,
            title="Test",
            mode="master",
            complexity_tier="master",
            player_count_support="solo",
        )
    )
    await session.flush()
    stats = dict(
        max_health=30, health=30, attack=9, armor=4, speed=5, accuracy=100, luck=50
    )
    combat = start_combat(
        "encounter",
        Combatant(actor_id="a", side="player", **stats),
        Combatant(actor_id="z", side="opponent", **stats),
    )
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=user_id,
        scenario_version=1,
        scenario_snapshot={"mode": "master"},
        state={"_combat": combat.model_dump(mode="json")},
    )
    session.add(playthrough)
    await session.flush()
    participant = Participant(
        playthrough_id=playthrough.playthrough_id,
        user_id=user_id,
        role="owner",
        turn_order_position=1,
    )
    session.add(participant)
    await session.commit()
    return playthrough.playthrough_id, participant.participant_id, user_id


def attack(operation_id=None, revision=0, actor="a", target="z"):
    return CombatAction(
        client_action_id=operation_id or uuid.uuid4(),
        expected_revision=revision,
        actor_id=actor,
        action_id="attack",
        target_id=target,
    )


async def run(session, ids, action, user_id=None):
    return await apply_combat_action(
        session,
        ids[0],
        ids[1],
        CurrentUser(user_id=user_id or ids[2], token_version=1),
        action,
    )


async def test_replay_changed_payload_and_auth(db_session):
    ids = await seed(db_session)
    command = attack()
    first = await run(db_session, ids, command)
    replay = await run(db_session, ids, command)
    assert first == replay
    assert first.state.revision == 1 and first.event.damage == 5
    with pytest.raises(CombatReplayConflictError):
        await run(db_session, ids, command.model_copy(update={"target_id": "a"}))
    with pytest.raises(ParticipantAccessDeniedError):
        await run(db_session, ids, command, user_id=uuid.uuid4())
    row = await db_session.get(Playthrough, ids[0])
    await db_session.refresh(row)
    assert row.state["_combat"]["revision"] == 1
    assert row.state["_combat"]["combatants"][1]["health"] == 25
    logs = (
        (
            await db_session.execute(
                select(TurnLog).where(TurnLog.playthrough_id == ids[0])
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1


async def test_stale_and_failed_write_leave_state_unchanged(db_session, monkeypatch):
    ids = await seed(db_session)
    with pytest.raises(CombatActionError):
        await run(db_session, ids, attack(revision=5))
    from app.repositories.turn_log_repo import TurnLogRepo

    async def fail(*args, **kwargs):
        raise RuntimeError("write failed")

    monkeypatch.setattr(TurnLogRepo, "create", fail)
    with pytest.raises(RuntimeError, match="write failed"):
        await run(db_session, ids, attack())
    await db_session.rollback()
    row = await db_session.get(Playthrough, ids[0])
    assert row.state["_combat"]["revision"] == 0
    assert row.turn_count == 0


async def test_concurrent_same_operation_commits_once(db_session):
    ids = await seed(db_session)
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    command = attack()

    async def execute():
        async with factory() as session:
            return await run(session, ids, command)

    first, second = await asyncio.gather(execute(), execute())
    assert first == second
    row = await db_session.get(Playthrough, ids[0])
    await db_session.refresh(row)
    assert row.state["_combat"]["revision"] == 1
    assert row.turn_count == 1


async def test_combat_receipt_cannot_be_replayed_as_narrative(db_session):
    from app.models.turn import TurnRequestInput
    from app.repositories.participant_repo import ParticipantRepo
    from app.repositories.turn_log_repo import TurnLogRepo
    from app.turn.steps.request_receiver import find_completed_turn

    ids = await seed(db_session)
    command = attack()
    await run(db_session, ids, command)
    narrative = TurnRequestInput(
        playthrough_id=ids[0],
        participant_id=ids[1],
        client_action_id=command.client_action_id,
        action_text="I wait.",
    )
    with pytest.raises(CombatReplayConflictError):
        await find_completed_turn(
            narrative,
            TurnLogRepo(db_session),
            ParticipantRepo(db_session),
            CurrentUser(user_id=ids[2], token_version=1),
        )


async def test_endpoint_returns_only_public_combat_data(db_session, async_client):
    from app.main import app
    from app.middleware.auth import get_current_user

    ids = await seed(db_session)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=ids[2], token_version=1
    )
    try:
        url = f"/v1/combat/{ids[0]}?participant_id={ids[1]}"
        initial = await async_client.get(url)
        assert initial.status_code == 200
        assert initial.json()["revision"] == 0
        assert initial.json()["legal_actions"][0]["target_id"] == "z"
        assert "luck" not in str(initial.json())
        payload = {
            "playthrough_id": str(ids[0]),
            "participant_id": str(ids[1]),
            "action": attack().model_dump(mode="json"),
        }
        result = await async_client.post("/v1/combat/action", json=payload)
        assert result.status_code == 200
        assert result.json()["state"]["revision"] == 1
        assert result.json()["event"]["damage"] == 5
        assert "luck" not in str(result.json())
        assert (await async_client.get(url)).json()["revision"] == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_concurrent_distinct_actions_accept_only_one_revision(db_session):
    ids = await seed(db_session)
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)

    async def execute(command):
        async with factory() as session:
            try:
                return await run(session, ids, command)
            except CombatActionError:
                return None

    first, second = await asyncio.gather(execute(attack()), execute(attack()))
    assert sum(result is not None for result in (first, second)) == 1
    row = await db_session.get(Playthrough, ids[0])
    await db_session.refresh(row)
    assert row.state["_combat"]["revision"] == 1


async def test_terminal_action_replays_from_fresh_session(db_session):
    ids = await seed(db_session)
    row = await db_session.get(Playthrough, ids[0])
    state = dict(row.state)
    combat = dict(state["_combat"])
    combatants = [dict(actor) for actor in combat["combatants"]]
    combatants[1]["health"] = 2
    combat["combatants"] = combatants
    row.state = {**state, "_combat": combat}
    await db_session.commit()
    command = attack()
    first = await run(db_session, ids, command)
    assert first.state.status == "opponent_defeated"
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    async with factory() as session:
        assert await run(session, ids, command) == first
        with pytest.raises(CombatActionError):
            await run(session, ids, attack(revision=1, actor="z", target="a"))


async def test_memory_receipt_is_atomic_with_combat(db_session):
    from app.db.models.memory_outbox import MemoryOutbox

    ids = await seed(db_session)
    row = await db_session.get(Playthrough, ids[0])
    row.memory_publish_revision = 1
    await db_session.commit()
    await run(db_session, ids, attack())
    rows = (
        (
            await db_session.execute(
                select(MemoryOutbox).where(MemoryOutbox.playthrough_id == ids[0])
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].item_kind == "turn" and rows[0].sequence == 1


async def test_cancelled_action_rolls_back_transaction(db_session, monkeypatch):
    from app.repositories.turn_log_repo import TurnLogRepo

    ids = await seed(db_session)

    async def cancel(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(TurnLogRepo, "create", cancel)
    with pytest.raises(asyncio.CancelledError):
        await run(db_session, ids, attack())
    assert not db_session.in_transaction()
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    async with factory() as fresh:
        row = await fresh.get(Playthrough, ids[0])
        assert row.state["_combat"]["revision"] == 0
        assert row.turn_count == 0


async def test_combat_turn_does_not_increment_play_count(db_session):
    from app.config import settings

    ids = await seed(db_session)
    row = await db_session.get(Playthrough, ids[0])
    row.turn_count = settings.play_count_increment_turn_threshold - 1
    scenario_id = row.scenario_id
    await db_session.commit()
    await run(db_session, ids, attack())
    scenario = await db_session.get(Scenario, scenario_id)
    await db_session.refresh(scenario)
    assert scenario.play_count == 0


async def test_lost_response_after_commit_replays_once(db_session, monkeypatch):
    ids = await seed(db_session)
    command = attack()
    commit = db_session.commit

    async def commit_then_disconnect():
        await commit()
        raise asyncio.CancelledError()

    monkeypatch.setattr(db_session, "commit", commit_then_disconnect)
    with pytest.raises(asyncio.CancelledError):
        await run(db_session, ids, command)
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    async with factory() as fresh:
        replay = await run(fresh, ids, command)
        assert replay.state.revision == 1
        assert replay.event.damage == 5
        row = await fresh.get(Playthrough, ids[0])
        assert row.turn_count == 1
        assert row.state["_combat"]["combatants"][1]["health"] == 25


async def test_endpoint_refuses_access_to_another_user(db_session, async_client):
    from app.main import app
    from app.middleware.auth import get_current_user

    ids = await seed(db_session)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid.uuid4(), token_version=1
    )
    try:
        url = f"/v1/combat/{ids[0]}?participant_id={ids[1]}"
        assert (await async_client.get(url)).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
