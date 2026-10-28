import uuid

from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.repositories.scenario_repo import ScenarioRepo
from sqlalchemy.ext.asyncio import AsyncSession

WELCOME_TAPE_ID = "tallis-v1"


async def enable_welcome_tape(session: AsyncSession, scenario_id: uuid.UUID) -> None:
    scenario = await ScenarioRepo(session).get_by_id_for_update(scenario_id)
    if scenario is None:
        raise ScenarioNotFoundError()
    world = dict(scenario.world_data or {})
    current = world.get("presentation", {})
    presentation = dict(current) if isinstance(current, dict) else {}
    presentation["welcome_tape_id"] = WELCOME_TAPE_ID
    world["presentation"] = presentation
    scenario.world_data = world
    await ScenarioRepo(session).update(scenario)
