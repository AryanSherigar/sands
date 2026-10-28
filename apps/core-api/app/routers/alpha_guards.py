import uuid
from typing import Annotated

from app.config import settings
from app.db.connection import get_db_session
from app.exceptions.alpha_exceptions import AlphaFeatureDisabledError
from app.exceptions.scenario_exceptions import ScenarioNotFoundError
from app.repositories.scenario_repo import ScenarioRepo
from app.services.scenario_access import is_reachable_in_alpha
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


async def forbid_in_alpha_mode() -> None:
    if settings.is_alpha_mode:
        raise AlphaFeatureDisabledError()


async def forbid_writes_in_alpha_mode(request: Request) -> None:
    if settings.is_alpha_mode and request.method not in READ_ONLY_METHODS:
        raise AlphaFeatureDisabledError()


async def restrict_to_alpha_scenario(
    scenario_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> None:
    if not settings.is_alpha_mode:
        return
    if not await is_reachable_in_alpha(ScenarioRepo(session), scenario_id):
        raise ScenarioNotFoundError()
