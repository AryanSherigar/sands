"""Integration tests for the player action size cap inside the turn pipeline."""

import json
import uuid

import pytest
from app.config import settings
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.services.rate_limit.exemption_service import get_exemption_service
from app.services.rate_limit.quota_service import QuotaService, user_quota_key
from app.turn import pipeline
from app.turn.steps import ai_orchestrator
from session_factories import committed_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DAY = 86400
SMALL_CAP = 25
OVERSIZED_ACTION = "I search the room carefully. " * 10
EVENT_NAME = "input_truncated"


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
            title="Limit Scenario",
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


@pytest.fixture
def quota_service(rate_limit_enabled) -> QuotaService:
    return QuotaService(rate_limit_enabled, get_exemption_service())


@pytest.fixture(autouse=True)
def small_cap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "turn_action_max_chars", SMALL_CAP)


@pytest.fixture
def seen_prompts(monkeypatch) -> list[str]:
    prompts: list[str] = []

    async def fake_stream(system_instruction: str, prompt: str, timeout_seconds: int):
        prompts.append(prompt)
        yield "The cave is dark."

    monkeypatch.setattr(
        ai_orchestrator.narration_router, "stream_narration", fake_stream
    )
    return prompts


async def _run(db_session, playthrough, participant, quota_service, action_text, **kw):
    turn_input = TurnRequestInput(
        client_action_id=kw.pop("client_action_id", uuid.uuid4()),
        playthrough_id=playthrough.playthrough_id,
        participant_id=participant.participant_id,
        action_text=action_text,
    )
    response = await pipeline.run_turn(
        turn_input,
        await committed_factory(db_session),
        CurrentUser(user_id=participant.user_id, token_version=1),
        quota_service,
    )
    return [event async for event in response.body_iterator]


async def test_over_cap_action_streams_notice_first_and_stores_truncated_text(
    db_session, quota_service, seen_prompts
) -> None:
    playthrough, participant = await _seed(db_session)

    events = await _run(
        db_session, playthrough, participant, quota_service, OVERSIZED_ACTION
    )

    assert events[0].event == EVENT_NAME
    assert json.loads(events[0].data) == {
        "original_length": len(OVERSIZED_ACTION.strip()),
        "max_length": SMALL_CAP,
    }
    assert events[-1].event == "done"
    turn_log = (
        await db_session.execute(
            select(TurnLog).where(TurnLog.playthrough_id == playthrough.playthrough_id)
        )
    ).scalar_one()
    assert turn_log.action_text == OVERSIZED_ACTION.strip()[:SMALL_CAP]
    assert OVERSIZED_ACTION.strip()[: SMALL_CAP + 1] not in seen_prompts[0]


async def test_truncation_still_spends_exactly_one_turn_unit(
    db_session, quota_service, seen_prompts
) -> None:
    playthrough, participant = await _seed(db_session)

    await _run(db_session, playthrough, participant, quota_service, OVERSIZED_ACTION)

    used = await quota_service.store.current_count(
        user_quota_key("turn", participant.user_id), DAY
    )
    assert used == 1


async def test_under_cap_action_emits_no_notice(
    db_session, quota_service, seen_prompts
) -> None:
    playthrough, participant = await _seed(db_session)

    events = await _run(db_session, playthrough, participant, quota_service, "look")

    assert EVENT_NAME not in [event.event for event in events]


async def test_replay_of_a_truncated_turn_emits_no_notice(
    db_session, quota_service, seen_prompts
) -> None:
    playthrough, participant = await _seed(db_session)
    client_action_id = uuid.uuid4()
    await _run(
        db_session,
        playthrough,
        participant,
        quota_service,
        OVERSIZED_ACTION,
        client_action_id=client_action_id,
    )

    replayed = await _run(
        db_session,
        playthrough,
        participant,
        quota_service,
        OVERSIZED_ACTION,
        client_action_id=client_action_id,
    )

    assert EVENT_NAME not in [event.event for event in replayed]
