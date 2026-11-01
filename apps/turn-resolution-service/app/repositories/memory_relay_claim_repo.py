"""Short transactions claiming and fencing relay batches."""

import uuid
from datetime import timedelta

from app.db.models.memory_relay_claim import MemoryRelayClaim
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


class MemoryRelayClaimRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def acquire(
        self, playthrough_id: uuid.UUID, lease_seconds: float
    ) -> MemoryRelayClaim | None:
        await self.session.execute(
            insert(MemoryRelayClaim)
            .values(
                playthrough_id=playthrough_id,
                delivery_id=uuid.uuid4(),
                ownership_token=uuid.uuid4(),
                lease_expires_at=func.now(),
                outbox_ids=[],
            )
            .on_conflict_do_nothing(index_elements=[MemoryRelayClaim.playthrough_id])
        )
        claim = await self.session.scalar(
            select(MemoryRelayClaim)
            .where(
                MemoryRelayClaim.playthrough_id == playthrough_id,
                MemoryRelayClaim.lease_expires_at <= func.now(),
            )
            .with_for_update(skip_locked=True)
        )
        if claim is None:
            return None
        claim.ownership_token = uuid.uuid4()
        claim.lease_expires_at = await self.session.scalar(
            select(func.now() + timedelta(seconds=lease_seconds))
        )
        return claim

    async def get_owned(
        self, playthrough_id: uuid.UUID, ownership_token: uuid.UUID
    ) -> MemoryRelayClaim | None:
        return await self.session.scalar(
            select(MemoryRelayClaim)
            .where(
                MemoryRelayClaim.playthrough_id == playthrough_id,
                MemoryRelayClaim.ownership_token == ownership_token,
            )
            .with_for_update()
        )

    async def release(self, claim: MemoryRelayClaim) -> None:
        claim.lease_expires_at = await self.session.scalar(select(func.now()))

    async def remove(self, claim: MemoryRelayClaim) -> None:
        await self.session.execute(
            delete(MemoryRelayClaim).where(
                MemoryRelayClaim.playthrough_id == claim.playthrough_id,
                MemoryRelayClaim.ownership_token == claim.ownership_token,
            )
        )
