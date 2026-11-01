"""Integration tests for daily quotas inside the turn pipeline."""

import json
import uuid

import pytest
from app.config import settings
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.rate_limit_exceptions import RateLimitExceededError
from app.exceptions.turn_exceptions import NarrationGenerationError
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.services.rate_limit.exemption_service import get_exemption_service
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService, user_quota_key
from app.turn import pipeline
from app.turn.steps import ai_orchestrator
from app.turn.steps.state_writer import SceneImageResult
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
            title="Quota Scenario",
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


def _turn_input(
    playthrough: Playthrough, participant: Participant, **overrides
) -> TurnRequestInput:
    return TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text="I look around.",
        **overrides,
    )


@pytest.fixture
def quota_service(rate_limit_enabled) -> QuotaService:
    return QuotaService(rate_limit_enabled, get_exemption_service())


@pytest.fixture
def fake_narration(monkeypatch) -> None:
    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        yield "The cave is dark."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )


async def _run(db_session, playthrough, participant, quota_service, **overrides):
    response = await pipeline.run_turn(
        _turn_input(playthrough, participant, **overrides),
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
        quota_service,
    )
    return [event async for event in response.body_iterator]


async def test_exhausted_turn_quota_refuses_before_streaming(
    db_session, quota_service, fake_narration, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "quota_turn_per_user", 0)
    playthrough, participant = await _seed(db_session)

    with pytest.raises(RateLimitExceededError) as caught:
        await _run(db_session, playthrough, participant, quota_service)

    assert caught.value.scope == QuotaFeature.TURN.value


async def test_scene_image_quota_spent_skips_image_with_notice(
    db_session, quota_service, fake_narration, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "quota_scene_image_per_user", 0)
    was_generated: list[bool] = []

    async def fake_generate(*args, **kwargs) -> SceneImageResult:
        was_generated.append(True)
        return SceneImageResult(image_url="u", location_id=None, scene_image_prompt="p")

    monkeypatch.setattr(pipeline, "_generate_turn_scene_image", fake_generate)
    playthrough, participant = await _seed(db_session)

    events = await _run(
        db_session, playthrough, participant, quota_service, action_mode="see"
    )

    event_types = [event.event for event in events]
    assert "quota_notice" in event_types
    assert "scene_image" not in event_types
    assert event_types[-1] == "done"
    notice = json.loads(next(e for e in events if e.event == "quota_notice").data)
    assert notice["feature"] == "scene_image"
    assert notice["code"] == "quota_exceeded"
    assert not was_generated


async def test_failed_scene_image_refunds_its_unit(
    db_session, quota_service, fake_narration, monkeypatch
) -> None:
    async def failed_generate(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(pipeline, "_generate_turn_scene_image", failed_generate)
    playthrough, participant = await _seed(db_session)

    await _run(db_session, playthrough, participant, quota_service, action_mode="see")

    used = await quota_service.store.current_count(
        user_quota_key("scene_image", participant.user_id), DAY
    )
    assert used == 0


async def test_voice_quota_spent_skips_audio_with_notice(
    db_session, quota_service, fake_narration, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "quota_tts_narration_per_user", 0)
    playthrough, participant = await _seed(db_session)

    events = await _run(
        db_session,
        playthrough,
        participant,
        quota_service,
        voice_output_requested=True,
    )

    notices = [json.loads(e.data) for e in events if e.event == "quota_notice"]
    assert [notice["feature"] for notice in notices] == ["tts_narration"]
    assert events[-1].event == "done"


async def test_narration_failure_refunds_turn_unit(
    db_session, quota_service, monkeypatch
) -> None:
    async def failing_narration(*args, **kwargs):
        raise NarrationGenerationError()
        yield  # pragma: no cover

    monkeypatch.setattr(
        pipeline.ai_orchestrator, "generate_narration", failing_narration
    )
    playthrough, participant = await _seed(db_session)

    await _run(db_session, playthrough, participant, quota_service)

    used = await quota_service.store.current_count(
        user_quota_key("turn", participant.user_id), DAY
    )
    assert used == 0


async def test_successful_turn_keeps_its_unit(
    db_session, quota_service, fake_narration
) -> None:
    playthrough, participant = await _seed(db_session)

    await _run(db_session, playthrough, participant, quota_service)

    used = await quota_service.store.current_count(
        user_quota_key("turn", participant.user_id), DAY
    )
    assert used == 1
