"""Shared seeding and turn-driving helpers for pipeline integration tests."""

import uuid

from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.turn import pipeline
from session_factories import committed_factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import ServerSentEvent


class FakeCandidate:
    content = "fake-model-turn-content"


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.function_calls = []
        self.text = text
        self.candidates = [FakeCandidate()]


def narrator(text: str, seen_prompts: list[str] | None = None):
    async def _generate(system_instruction, contents, timeout_seconds, tools):
        if seen_prompts is not None:
            seen_prompts.append(str(system_instruction) + str(contents))
        yield FakeResponse(text)

    return _generate


async def seed_master_playthrough(
    session: AsyncSession, snapshot: dict[str, object], state: dict[str, object]
) -> tuple[Playthrough, Participant]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        User(user_id=user_id, display_name="Tester", auth_provider_id=str(uuid.uuid4()))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=user_id,
            title="Night Desk",
            mode="master",
            complexity_tier="master",
            player_count_support="solo",
        )
    )
    await session.flush()
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=user_id,
        scenario_version=1,
        scenario_snapshot=snapshot,
        state=state,
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


async def arm_pending_check(session: AsyncSession, playthrough: Playthrough) -> None:
    """Flip the open rule check to armed, keeping its stamped window, so a test
    can answer it the way a player who has read the narration would."""
    state = dict(await stored_state(session, playthrough))
    pending = state.get("_pending_check")
    if not isinstance(pending, dict) or pending.get("is_armed", True):
        return
    playthrough.state = {**state, "_pending_check": {**pending, "is_armed": True}}
    await session.flush()


async def take_turn(
    session: AsyncSession,
    playthrough: Playthrough,
    participant: Participant,
    client_action_id: uuid.UUID | None = None,
    **request_fields,
) -> list[ServerSentEvent]:
    fields = {"action_text": "I wait.", **request_fields}
    if fields.get("action_kind") == "check_report":
        await arm_pending_check(session, playthrough)
    response = await pipeline.run_turn(
        TurnRequestInput(
            client_action_id=client_action_id or uuid.uuid4(),
            playthrough_id=playthrough.playthrough_id,
            participant_id=participant.participant_id,
            **fields,
        ),
        await committed_factory(session),
        CurrentUser(user_id=participant.user_id, token_version=1),
    )
    return [event async for event in response.body_iterator]


async def stored_state(
    session: AsyncSession, playthrough: Playthrough
) -> dict[str, object]:
    stmt = select(Playthrough).where(
        Playthrough.playthrough_id == playthrough.playthrough_id
    )
    stored = (await session.execute(stmt)).scalars().first()
    await session.refresh(stored)
    return stored.state
