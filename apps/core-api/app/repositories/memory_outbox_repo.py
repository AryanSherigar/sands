"""MemoryOutbox data repository for direct database operations."""

import uuid
from datetime import datetime

from app.db.models.memory_outbox import (
    ITEM_KIND_PARTICIPANTS,
    ITEM_KIND_REGISTER,
    MemoryOutbox,
)
from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

REGISTER_SEQUENCE = 0
PARTICIPANTS_UNIQUE_CONSTRAINT = "uq_memory_outbox_playthrough_kind_sequence"
# NOTE: Mirrors the codes the TRS relay writes when it closes an undeliverable row.
DEAD_LETTER_ERROR_CODES = ("turn_log_missing", "participant_missing")


class MemoryOutboxRepo:
    """Repository managing direct SQLAlchemy queries for MemoryOutbox entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_register_row(
        self, playthrough_id: uuid.UUID, payload: dict[str, object]
    ) -> MemoryOutbox:
        """Insert the registration row for a new playthrough."""
        row = MemoryOutbox(
            playthrough_id=playthrough_id,
            item_kind=ITEM_KIND_REGISTER,
            sequence=REGISTER_SEQUENCE,
            payload=payload,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def upsert_participants_row(
        self, playthrough_id: uuid.UUID, sequence: int, payload: dict[str, object]
    ) -> None:
        """Queue the participant list for `sequence`, re-queuing a delivered row.

        The payload always holds the full list and memory merges it by id, so
        redelivering a replaced row is safe.
        """
        statement = insert(MemoryOutbox).values(
            playthrough_id=playthrough_id,
            item_kind=ITEM_KIND_PARTICIPANTS,
            sequence=sequence,
            payload=payload,
        )
        statement = statement.on_conflict_do_update(
            constraint=PARTICIPANTS_UNIQUE_CONSTRAINT,
            set_={
                "payload": payload,
                "delivered_at": None,
                "attempt_count": 0,
                "last_error": None,
            },
        )
        await self.session.execute(statement)

    async def delete_delivered_before(self, cutoff: datetime, limit: int) -> int:
        """Delete up to `limit` delivered rows older than `cutoff`.

        Undelivered rows and dead-lettered orphans are kept: a dead-lettered row
        is closed with `delivered_at` set, so it is told apart by its error code.
        """
        expired = _delivered_before(select(MemoryOutbox.outbox_id), cutoff).limit(limit)
        result = await self.session.execute(
            delete(MemoryOutbox).where(MemoryOutbox.outbox_id.in_(expired))
        )
        return result.rowcount

    async def count_delivered_before(self, cutoff: datetime) -> int:
        stmt = _delivered_before(select(func.count()), cutoff).select_from(MemoryOutbox)
        return int((await self.session.execute(stmt)).scalar_one())


def _delivered_before(stmt: Select, cutoff: datetime) -> Select:
    is_dead_lettered = MemoryOutbox.last_error.in_(DEAD_LETTER_ERROR_CODES)
    return (
        stmt.where(MemoryOutbox.delivered_at.is_not(None))
        .where(MemoryOutbox.delivered_at < cutoff)
        .where(or_(MemoryOutbox.last_error.is_(None), ~is_dead_lettered))
    )
