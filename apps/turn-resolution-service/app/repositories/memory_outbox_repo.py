"""MemoryOutbox data repository for direct database operations."""

import uuid

from app.db.models.memory_outbox import (
    ITEM_KIND_FLUSH,
    ITEM_KIND_PARTICIPANTS,
    ITEM_KIND_REGISTER,
    ITEM_KIND_TURN,
    MemoryOutbox,
)
from sqlalchemy import Select, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

KIND_ORDER = case(
    (MemoryOutbox.item_kind == ITEM_KIND_REGISTER, 0),
    (MemoryOutbox.item_kind == ITEM_KIND_TURN, 1),
    (MemoryOutbox.item_kind == ITEM_KIND_PARTICIPANTS, 2),
    else_=3,
)


def _undelivered_in_delivery_order(
    playthrough_id: uuid.UUID, limit: int
) -> Select[tuple[MemoryOutbox]]:
    return (
        select(MemoryOutbox)
        .where(
            MemoryOutbox.playthrough_id == playthrough_id,
            MemoryOutbox.delivered_at.is_(None),
        )
        .order_by(MemoryOutbox.sequence, KIND_ORDER, MemoryOutbox.outbox_id)
        .limit(limit)
    )


class MemoryOutboxRepo:
    """Repository managing direct SQLAlchemy queries for MemoryOutbox entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_turn_row(
        self, playthrough_id: uuid.UUID, turn_number: int, turn_id: uuid.UUID
    ) -> MemoryOutbox:
        """Insert the delivery row for a turn inside the caller's transaction."""
        return await self._add_row(playthrough_id, ITEM_KIND_TURN, turn_number, turn_id)

    async def add_flush_row(
        self, playthrough_id: uuid.UUID, turn_number: int
    ) -> MemoryOutbox:
        """Insert the ending flush row inside the caller's transaction."""
        return await self._add_row(playthrough_id, ITEM_KIND_FLUSH, turn_number, None)

    async def list_playthrough_ids_with_undelivered(
        self, limit: int
    ) -> list[uuid.UUID]:
        """Playthroughs with pending rows, the one waiting longest first."""
        stmt = (
            select(MemoryOutbox.playthrough_id)
            .where(MemoryOutbox.delivered_at.is_(None))
            .group_by(MemoryOutbox.playthrough_id)
            .order_by(func.min(MemoryOutbox.outbox_id))
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def lock_deliverable_prefix(
        self, playthrough_id: uuid.UUID, limit: int
    ) -> list[MemoryOutbox]:
        """Lock the playthrough's oldest undelivered rows, or none if another
        relay holds any row ahead of them.

        SKIP LOCKED alone would let a second relay deliver rows 4-5 while the
        first still holds 1-3; the locked rows are used only when they are an
        exact prefix of the delivery order.
        """
        expected_ids = await self._peek_delivery_order(playthrough_id, limit)
        locked = await self._lock_delivery_order(playthrough_id, limit)
        locked_ids = [row.outbox_id for row in locked]
        return locked if locked_ids == expected_ids[: len(locked_ids)] else []

    async def _peek_delivery_order(
        self, playthrough_id: uuid.UUID, limit: int
    ) -> list[int]:
        stmt = _undelivered_in_delivery_order(playthrough_id, limit)
        result = await self.session.execute(
            stmt.with_only_columns(MemoryOutbox.outbox_id)
        )
        return list(result.scalars().all())

    async def _lock_delivery_order(
        self, playthrough_id: uuid.UUID, limit: int
    ) -> list[MemoryOutbox]:
        stmt = _undelivered_in_delivery_order(playthrough_id, limit)
        result = await self.session.execute(stmt.with_for_update(skip_locked=True))
        return list(result.scalars().all())

    async def mark_delivered(self, outbox_ids: list[int]) -> None:
        await self.session.execute(
            update(MemoryOutbox)
            .where(MemoryOutbox.outbox_id.in_(outbox_ids))
            .values(delivered_at=func.now())
        )

    async def mark_dead_lettered(self, outbox_ids: list[int], error_code: str) -> None:
        """Close rows that can never be delivered, keeping why in last_error."""
        await self.session.execute(
            update(MemoryOutbox)
            .where(MemoryOutbox.outbox_id.in_(outbox_ids))
            .values(delivered_at=func.now(), last_error=error_code)
        )

    async def record_failure(self, outbox_ids: list[int], error_code: str) -> None:
        await self.session.execute(
            update(MemoryOutbox)
            .where(MemoryOutbox.outbox_id.in_(outbox_ids))
            .values(attempt_count=MemoryOutbox.attempt_count + 1, last_error=error_code)
        )

    async def _add_row(
        self,
        playthrough_id: uuid.UUID,
        item_kind: str,
        sequence: int,
        turn_id: uuid.UUID | None,
    ) -> MemoryOutbox:
        row = MemoryOutbox(
            playthrough_id=playthrough_id,
            item_kind=item_kind,
            sequence=sequence,
            turn_id=turn_id,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def has_undelivered_through(
        self, playthrough_id: uuid.UUID, sequence: int
    ) -> bool:
        """True when a row at or before `sequence` has not reached memory yet."""
        stmt = (
            select(MemoryOutbox.outbox_id)
            .where(
                MemoryOutbox.playthrough_id == playthrough_id,
                MemoryOutbox.delivered_at.is_(None),
                MemoryOutbox.sequence <= sequence,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).first() is not None
