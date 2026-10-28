"""Shared FastAPI dependencies for owner-triggered achievement awarding."""

from datetime import UTC, datetime
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.services.achievement_service import (
    AchievementService,
    build_achievement_service,
)
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


def get_achievement_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> AchievementService:
    return build_achievement_service(session)


async def award_owner_achievements(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AchievementService, Depends(get_achievement_service)],
) -> None:
    """Runs before an owner-only handler so its response already sees new badges."""
    await service.evaluate_and_award(user.user_id, datetime.now(UTC))
