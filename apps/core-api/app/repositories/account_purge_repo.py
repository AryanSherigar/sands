"""Repository for the SQL an account purge needs across several entities."""

import uuid
from datetime import datetime

from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.memory_relay_claim import MemoryRelayClaim
from app.db.models.music_generation_job import MusicGenerationJob
from app.db.models.music_generation_log import MusicGenerationLog
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.share import PlaythroughShare
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from sqlalchemy import delete, exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

PUBLISHED_STATUS = "published"


def _is_retained_scenario_clause():
    has_playthroughs = exists().where(Playthrough.scenario_id == Scenario.scenario_id)
    return (Scenario.status == PUBLISHED_STATUS) | has_playthroughs


class AccountPurgeRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_user_ids_due_for_purge(
        self, cutoff: datetime, limit: int
    ) -> list[uuid.UUID]:
        stmt = (
            select(User.user_id)
            .where(User.deletion_requested_at.is_not(None))
            .where(User.deletion_requested_at <= cutoff)
            .order_by(User.deletion_requested_at)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def ensure_placeholder_user(self, placeholder_id: uuid.UUID) -> None:
        existing = await self.session.get(User, placeholder_id)
        if existing is None:
            self.session.add(
                User(
                    user_id=placeholder_id,
                    display_name="Deleted user",
                    auth_provider_id=f"system:{placeholder_id}",
                )
            )
            await self.session.flush()

    async def list_playthrough_ids(
        self, user_id: uuid.UUID, limit: int
    ) -> list[uuid.UUID]:
        stmt = (
            select(Playthrough.playthrough_id)
            .where(Playthrough.created_by == user_id)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_outbox_rows(self, playthrough_ids: list[uuid.UUID]) -> None:
        for model in (MemoryRelayClaim, MemoryOutbox):
            await self.session.execute(
                delete(model).where(model.playthrough_id.in_(playthrough_ids))
            )

    async def delete_playthroughs(self, playthrough_ids: list[uuid.UUID]) -> None:
        for model in (
            MemoryRelayClaim,
            MemoryOutbox,
            TurnLog,
            PlaythroughShare,
            Participant,
        ):
            await self.session.execute(
                delete(model).where(model.playthrough_id.in_(playthrough_ids))
            )
        await self.session.execute(
            delete(Playthrough).where(Playthrough.playthrough_id.in_(playthrough_ids))
        )

    async def delete_participations(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(Participant).where(Participant.user_id == user_id)
        )

    async def list_deletable_scenario_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = (
            select(Scenario.scenario_id)
            .where(Scenario.creator_id == user_id)
            .where(~_is_retained_scenario_clause())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_deletable_scenario_cover_urls(self, user_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Scenario.cover_image_url)
            .where(Scenario.creator_id == user_id)
            .where(~_is_retained_scenario_clause())
            .where(Scenario.cover_image_url.is_not(None))
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def reassign_retained_scenarios(
        self, user_id: uuid.UUID, placeholder_id: uuid.UUID
    ) -> None:
        await self.session.execute(
            update(Scenario)
            .where(Scenario.creator_id == user_id)
            .where(_is_retained_scenario_clause())
            .values(creator_id=placeholder_id)
        )

    async def delete_music_generation_records(self, user_id: uuid.UUID) -> None:
        for model in (MusicGenerationJob, MusicGenerationLog):
            await self.session.execute(delete(model).where(model.creator_id == user_id))

    async def delete_owned_scenarios(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(Scenario).where(Scenario.creator_id == user_id)
        )

    async def delete_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(delete(User).where(User.user_id == user_id))
