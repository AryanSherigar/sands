"""Writes the Night Desk scenario to the database through the shared seeding code."""

import uuid

from scripts.night_desk import map_data
from scripts.night_desk.builder import NightDeskScenario
from scripts.night_desk.ids import IDS
from scripts.seeding import persist as seeding_persist
from scripts.seeding.types import MapSeed
from sqlalchemy.ext.asyncio import AsyncSession


def floor_map() -> MapSeed:
    return MapSeed(
        name=map_data.MAP_NAME,
        image_url=None,
        pins=map_data.PINS,
        connections=map_data.CONNECTIONS,
        start_slug=map_data.START_SLUG,
    )


async def persist(
    session: AsyncSession, built: NightDeskScenario, creator_id: uuid.UUID
) -> None:
    await seeding_persist.persist(session, built, creator_id, IDS, [floor_map()])
