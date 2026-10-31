"""Inert-data counter for the `composure` tool: composure minigames."""

import uuid

from app.repositories.minigame_repo import MinigameRepo
from app.tools.data_counters import register_data_counter
from sqlalchemy.ext.asyncio import AsyncSession

TOOL_KEY = "composure"


async def count_composure_minigames(
    session: AsyncSession, scenario_id: uuid.UUID
) -> int:
    return await MinigameRepo(session).count_composure_by_scenario(scenario_id)


register_data_counter(TOOL_KEY, count_composure_minigames)
