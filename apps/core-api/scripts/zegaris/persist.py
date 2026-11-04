"""Writes the Zegaris scenario to the database through the shared seeding code."""

import uuid

from scripts.seeding import persist as seeding_persist
from scripts.zegaris.builder import ZegarisScenario
from scripts.zegaris.ids import IDS
from sqlalchemy.ext.asyncio import AsyncSession


async def persist(
    session: AsyncSession, built: ZegarisScenario, creator_id: uuid.UUID
) -> None:
    await seeding_persist.persist(session, built, creator_id, IDS, built.maps)
