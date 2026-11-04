"""Writes the Aldermark scenario row (idempotent, replace-in-place)."""

import uuid

from app.db.models.scenario import Scenario
from app.services.scenario_edit_guard import ensure_not_publishing
from scripts.aldermark.ids import SCENARIO_ID
from sqlalchemy.ext.asyncio import AsyncSession

DRAFT_STATUS = "draft"


async def persist(
    session: AsyncSession, columns: dict[str, object], creator_id: uuid.UUID
) -> Scenario:
    scenario = await session.get(Scenario, SCENARIO_ID)
    if scenario is None:
        scenario = Scenario(scenario_id=SCENARIO_ID, creator_id=creator_id)
        session.add(scenario)
    else:
        ensure_not_publishing(scenario)
    for column, value in columns.items():
        setattr(scenario, column, value)
    scenario.status = DRAFT_STATUS
    await session.flush()
    return scenario
