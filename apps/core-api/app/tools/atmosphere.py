"""Inert-data counter for the `atmosphere` tool: conditions that still carry a
sensory cue."""

import uuid

from app.repositories.condition_repo import ConditionRepo
from app.tools.data_counters import register_data_counter
from sqlalchemy.ext.asyncio import AsyncSession

TOOL_KEY = "atmosphere"


async def count_cue_conditions(session: AsyncSession, scenario_id: uuid.UUID) -> int:
    return await ConditionRepo(session).count_with_cues_by_scenario(scenario_id)


register_data_counter(TOOL_KEY, count_cue_conditions)
