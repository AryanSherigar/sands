"""Pipeline behaviour in alpha mode: no scene images, no audio, one scenario."""

import uuid

import pytest
from app.config import settings
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.alpha_exceptions import AlphaScenarioOnlyError
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.services.rate_limit.exemption_service import get_exemption_service
from app.services.rate_limit.quota_service import QuotaService, user_quota_key
from app.turn import pipeline
from app.turn.steps import ai_orchestrator
from session_factories import committed_factory
from sqlalchemy.ext.asyncio import AsyncSession

DAY = 86400


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
            title="Alpha Scenario",
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
        scenario_snapshot={"narrator_persona": "A voice.", "world_data": "A cave."},
        state={"setup": {}, "narrative": {"opening_prompt": None}},
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


def _turn_input(playthrough, participant, **overrides) -> TurnRequestInput:
    fields = {"client_action_id": uuid.uuid4(), "action_text": "I look around."}
    fields.update(overrides)
    return TurnRequestInput(
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        **fields,
    )


async def _run(db_session, playthrough, participant, quota_service=None, **overrides):
    response = await pipeline.run_turn(
        _turn_input(playthrough, participant, **overrides),
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
        quota_service,
    )
    return [event async for event in response.body_iterator]


@pytest.fixture
def quota_service(rate_limit_enabled) -> QuotaService:
    return QuotaService(rate_limit_enabled, get_exemption_service())


@pytest.fixture
def narration_calls(monkeypatch) -> list[bool]:
    calls: list[bool] = []

    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        calls.append(True)
        yield "The cave is dark."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )
    return calls


@pytest.fixture
def media_calls(monkeypatch) -> list[str]:
    calls: list[str] = []

    async def fake_image(*args, **kwargs):
        calls.append("image")

    async def fake_audio(*args, **kwargs):
        calls.append("audio")

    monkeypatch.setattr(pipeline, "_generate_turn_scene_image", fake_image)
    monkeypatch.setattr(pipeline, "_generate_turn_narration_audio", fake_audio)
    return calls


def _enter_alpha_mode(monkeypatch, scenario_id: uuid.UUID) -> None:
    monkeypatch.setattr(settings, "is_alpha_mode", True)
    monkeypatch.setattr(settings, "alpha_scenario_id", scenario_id)


async def test_alpha_mode_skips_scene_image_and_audio_without_spending_quota(
    db_session, quota_service, narration_calls, media_calls, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session)
    _enter_alpha_mode(monkeypatch, playthrough.scenario_id)

    events = await _run(
        db_session,
        playthrough,
        participant,
        quota_service,
        action_mode="see",
        voice_output_requested=True,
    )

    event_types = [event.event for event in events]
    assert media_calls == []
    assert "quota_notice" not in event_types
    assert "scene_image" not in event_types
    assert "narration_audio" not in event_types
    assert event_types[-1] == "done"
    for feature in ("scene_image", "tts_narration"):
        key = user_quota_key(feature, participant.user_id)
        assert await quota_service.store.current_count(key, DAY) == 0


async def test_alpha_mode_still_generates_media_when_it_is_off(
    db_session, quota_service, narration_calls, media_calls
) -> None:
    playthrough, participant = await _seed(db_session)

    await _run(
        db_session,
        playthrough,
        participant,
        quota_service,
        action_mode="see",
        voice_output_requested=True,
    )

    assert media_calls == ["image", "audio"]


async def test_turn_on_the_alpha_scenario_completes(
    db_session, narration_calls, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session)
    _enter_alpha_mode(monkeypatch, playthrough.scenario_id)

    events = await _run(db_session, playthrough, participant)

    assert events[-1].event == "done"
    assert narration_calls == [True]


async def test_turn_on_another_scenario_is_refused_before_narration(
    db_session, narration_calls, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session)
    _enter_alpha_mode(monkeypatch, uuid.uuid4())

    with pytest.raises(AlphaScenarioOnlyError):
        await _run(db_session, playthrough, participant)

    assert narration_calls == []


async def test_retried_action_on_another_scenario_is_refused_not_replayed(
    db_session, narration_calls, monkeypatch
) -> None:
    playthrough, participant = await _seed(db_session)
    turn_input = _turn_input(playthrough, participant)
    current_user = CurrentUser(user_id=participant.user_id, token_version=1)
    first = await pipeline.run_turn(
        turn_input, await committed_factory(db_session), current_user
    )
    [event async for event in first.body_iterator]
    _enter_alpha_mode(monkeypatch, uuid.uuid4())

    with pytest.raises(AlphaScenarioOnlyError):
        await pipeline.run_turn(
            turn_input, await committed_factory(db_session), current_user
        )
