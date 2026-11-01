"""Replay of a retried client_action_id through the real pipeline and Postgres."""

import json
import uuid

import pytest
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.turn_exceptions import ParticipantAccessDeniedError
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.turn import pipeline
from app.turn.steps import ai_orchestrator
from session_factories import committed_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed(session: AsyncSession) -> tuple[Playthrough, Participant]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        User(user_id=user_id, display_name="Tester", auth_provider_id=str(uuid.uuid4()))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=user_id,
            title="Replay",
            mode="newbie",
            complexity_tier="newbie",
            player_count_support="solo",
        )
    )
    await session.flush()
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=user_id,
        scenario_version=1,
        scenario_snapshot={"world_data": {}},
        state={"setup": {}, "narrative": {}},
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
    await session.flush()
    return playthrough, participant


def _input(playthrough, participant, client_action_id, text="I step forward."):
    return TurnRequestInput(
        client_action_id=client_action_id,
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text=text,
    )


async def _run(session, turn_input, user_id):
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(session),
        CurrentUser(user_id=user_id, token_version=1),
    )
    return [event async for event in response.body_iterator]


def _install_narrator(monkeypatch) -> list[str]:
    prompts: list[str] = []

    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        prompts.append(prompt)
        yield "You step into the corridor."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )
    return prompts


async def test_retry_replays_the_stored_turn_without_a_second_narration(
    db_session: AsyncSession, monkeypatch
) -> None:
    prompts = _install_narrator(monkeypatch)
    playthrough, participant = await _seed(db_session)
    action_id = uuid.uuid4()
    turn_input = _input(playthrough, participant, action_id)

    first = await _run(db_session, turn_input, participant.user_id)
    replay = await _run(db_session, turn_input, participant.user_id)

    assert [event.event for event in first] == ["narration", "done"]
    assert [(event.event, event.data) for event in replay] == [
        ("narration", "You step into the corridor."),
        ("done", first[-1].data),
    ]
    assert json.loads(first[-1].data)["turn_id"]
    assert len(prompts) == 1
    await db_session.refresh(playthrough)
    assert playthrough.turn_count == 1


async def test_retry_does_not_reserve_quota_again(
    db_session: AsyncSession, monkeypatch
) -> None:
    _install_narrator(monkeypatch)
    playthrough, participant = await _seed(db_session)
    turn_input = _input(playthrough, participant, uuid.uuid4())
    reservations: list[str] = []

    class _Quota:
        async def reserve_turn(self) -> None:
            reservations.append("reserve")

    monkeypatch.setattr(pipeline, "TurnQuota", lambda *args, **kwargs: _Quota())

    await _run(db_session, turn_input, participant.user_id)
    await _run(db_session, turn_input, participant.user_id)

    assert reservations == ["reserve"]


async def test_retry_of_a_turn_that_ended_the_playthrough_still_replays(
    db_session: AsyncSession, monkeypatch
) -> None:
    _install_narrator(monkeypatch)
    playthrough, participant = await _seed(db_session)
    turn_input = _input(playthrough, participant, uuid.uuid4())
    await _run(db_session, turn_input, participant.user_id)
    playthrough.status = "completed"
    await db_session.flush()

    replay = await _run(db_session, turn_input, participant.user_id)

    assert [event.event for event in replay] == ["narration", "done"]


async def test_retry_after_a_pending_check_was_proposed_still_replays(
    db_session: AsyncSession, monkeypatch
) -> None:
    _install_narrator(monkeypatch)
    playthrough, participant = await _seed(db_session)
    turn_input = _input(playthrough, participant, uuid.uuid4())
    await _run(db_session, turn_input, participant.user_id)
    playthrough.state = {
        **playthrough.state,
        "_pending_check": {"check_id": str(uuid.uuid4())},
    }
    await db_session.flush()

    replay = await _run(db_session, turn_input, participant.user_id)

    assert [event.event for event in replay] == ["narration", "done"]


async def test_a_new_client_action_id_is_a_new_turn(
    db_session: AsyncSession, monkeypatch
) -> None:
    prompts = _install_narrator(monkeypatch)
    playthrough, participant = await _seed(db_session)

    await _run(
        db_session, _input(playthrough, participant, uuid.uuid4()), participant.user_id
    )
    await _run(
        db_session,
        _input(playthrough, participant, uuid.uuid4(), "I open the door."),
        participant.user_id,
    )

    assert len(prompts) == 2
    await db_session.refresh(playthrough)
    assert playthrough.turn_count == 2


async def test_another_user_cannot_replay_someone_elses_turn(
    db_session: AsyncSession, monkeypatch
) -> None:
    _install_narrator(monkeypatch)
    playthrough, participant = await _seed(db_session)
    turn_input = _input(playthrough, participant, uuid.uuid4())
    await _run(db_session, turn_input, participant.user_id)

    with pytest.raises(ParticipantAccessDeniedError):
        await _run(db_session, turn_input, uuid.uuid4())


async def test_replay_includes_stored_media_urls(
    db_session: AsyncSession, monkeypatch
) -> None:
    from app.db.models.turn_log import TurnLog

    _install_narrator(monkeypatch)
    playthrough, participant = await _seed(db_session)
    turn_input = _input(playthrough, participant, uuid.uuid4())
    await _run(db_session, turn_input, participant.user_id)
    turn_log = (
        (
            await db_session.execute(
                select(TurnLog).where(
                    TurnLog.playthrough_id == playthrough.playthrough_id
                )
            )
        )
        .scalars()
        .one()
    )
    turn_log.image_url = "https://cdn.example/scene.png"
    turn_log.audio_url = "https://cdn.example/voice.mp3"
    await db_session.flush()

    replay = await _run(db_session, turn_input, participant.user_id)

    assert [(event.event, event.data) for event in replay] == [
        ("narration", "You step into the corridor."),
        ("scene_image", "https://cdn.example/scene.png"),
        ("narration_audio", "https://cdn.example/voice.mp3"),
        ("done", json.dumps({"turn_id": str(turn_log.turn_id)})),
    ]
