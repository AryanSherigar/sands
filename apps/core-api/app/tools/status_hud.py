"""Inert-data counter for the `status_hud` tool: display hints left on the
scenario's state_schema."""

import uuid

from app.repositories.scenario_repo import ScenarioRepo
from app.services.display_hints import STATUS_HUD_TOOL_KEY, count_display_hints
from app.tools.data_counters import register_data_counter
from sqlalchemy.ext.asyncio import AsyncSession


async def count_display_hint_fields(
    session: AsyncSession, scenario_id: uuid.UUID
) -> int:
    scenario = await ScenarioRepo(session).get_by_id(scenario_id)
    if scenario is None:
        return 0
    return count_display_hints(scenario.state_schema)


register_data_counter(STATUS_HUD_TOOL_KEY, count_display_hint_fields)
