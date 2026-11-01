"""Committed fixtures for tests that drive the memory outbox relay.

The relay opens its own sessions, so everything it reads must be committed.
"""

import uuid
from dataclasses import dataclass

from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

CANARY = "CANARY-PLAYER-TEXT-9f3a"


@dataclass(frozen=True)
class SeededPlaythrough:
    playthrough_id: uuid.UUID
    scenario_id: uuid.UUID
    participant_id: uuid.UUID
    user_id: uuid.UUID


async def seed_playthrough(session: AsyncSession) -> SeededPlaythrough:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        User(user_id=user_id, display_name="T", auth_provider_id=str(uuid.uuid4()))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=user_id,
            title="S",
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
        memory_publish_revision=0,
        state={},
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
    await session.commit()
    return SeededPlaythrough(
        playthrough.playthrough_id, scenario_id, participant.participant_id, user_id
    )


async def add_register_row(
    session: AsyncSession, seeded: SeededPlaythrough, payload: dict | None = None
) -> MemoryOutbox:
    row = MemoryOutbox(
        playthrough_id=seeded.playthrough_id,
        item_kind="register_playthrough",
        sequence=0,
        payload=payload
        if payload is not None
        else {
            "scenario_id": str(seeded.scenario_id),
            "publish_revision": 0,
            "player_entity": None,
            "setup_facts": [],
        },
    )
    session.add(row)
    await session.commit()
    return row


async def add_turn(
    session: AsyncSession,
    seeded: SeededPlaythrough,
    turn_number: int,
    tool_calls: list[dict] | None = None,
    accepted_delta: dict | None = None,
    participant_id: uuid.UUID | str | None = "default",
) -> tuple[TurnLog, MemoryOutbox]:
    turn_log = TurnLog(
        playthrough_id=seeded.playthrough_id,
        turn_number=turn_number,
        participant_id=(
            seeded.participant_id if participant_id == "default" else participant_id
        ),
        action_text=f"{CANARY} action {turn_number}",
        action_mode="say",
        narration_text=f"{CANARY} narration {turn_number}",
        tool_calls=tool_calls or [],
        accepted_delta=accepted_delta or {},
    )
    session.add(turn_log)
    await session.flush()
    row = MemoryOutbox(
        playthrough_id=seeded.playthrough_id,
        item_kind="turn",
        sequence=turn_number,
        turn_id=turn_log.turn_id,
    )
    session.add(row)
    await session.commit()
    return turn_log, row


async def add_flush(
    session: AsyncSession, seeded: SeededPlaythrough, sequence: int
) -> MemoryOutbox:
    row = MemoryOutbox(
        playthrough_id=seeded.playthrough_id, item_kind="flush", sequence=sequence
    )
    session.add(row)
    await session.commit()
    return row


async def add_participants_row(
    session: AsyncSession,
    seeded: SeededPlaythrough,
    sequence: int,
    payload: dict | None = None,
) -> MemoryOutbox:
    row = MemoryOutbox(
        playthrough_id=seeded.playthrough_id,
        item_kind="participants",
        sequence=sequence,
        payload=payload
        if payload is not None
        else {
            "participants": [
                {
                    "participant_id": str(seeded.participant_id),
                    "display_name": "Ada",
                }
            ]
        },
    )
    session.add(row)
    await session.commit()
    return row


async def reload_rows(
    session: AsyncSession, seeded: SeededPlaythrough
) -> list[MemoryOutbox]:
    session.expire_all()
    stmt = (
        select(MemoryOutbox)
        .where(MemoryOutbox.playthrough_id == seeded.playthrough_id)
        .order_by(MemoryOutbox.sequence, MemoryOutbox.outbox_id)
    )
    return list((await session.execute(stmt)).scalars().all())
