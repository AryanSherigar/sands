"""Writes the appraisal scenario to the database through the shared seeding code."""

import uuid

from scripts.reincarnated_aristocrat.builder import AppraisalScenario
from scripts.reincarnated_aristocrat.ids import IDS
from scripts.seeding import persist as seeding_persist
from sqlalchemy.ext.asyncio import AsyncSession


async def persist(
    session: AsyncSession, built: AppraisalScenario, creator_id: uuid.UUID
) -> None:
    await seeding_persist.persist(session, built, creator_id, IDS, built.maps)
