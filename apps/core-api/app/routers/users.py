"""FastAPI router for User Profile and activity endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.achievements import (
    OwnerAchievementResponse,
    PublicAchievementResponse,
)
from app.models.endings import EndingsResponse
from app.models.profile_overview import ProfileOverviewResponse
from app.models.user import (
    OnboardingCompleteRequest,
    UserPlaythroughSummary,
    UserProfileResponse,
    UserProfileUpdate,
    UserPublicProfileResponse,
    UserReviewSummary,
)
from app.repositories.endings_repo import EndingsRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.profile_overview_repo import ProfileOverviewRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.user_repo import UserRepo
from app.routers.achievement_deps import (
    award_owner_achievements,
    get_achievement_service,
)
from app.services.achievement_service import (
    AchievementService,
    build_achievement_service,
)
from app.services.endings_service import EndingsService
from app.services.profile_overview_service import ProfileOverviewService
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/users", tags=["Users"])


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> UserService:
    return UserService(
        user_repo=UserRepo(session),
        playthrough_repo=PlaythroughRepo(session),
    )


def get_profile_overview_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> ProfileOverviewService:
    return ProfileOverviewService(
        overview_repo=ProfileOverviewRepo(session),
        playthrough_repo=PlaythroughRepo(session),
        turn_log_repo=TurnLogRepo(session),
        endings_service=EndingsService(EndingsRepo(session)),
        achievement_service=build_achievement_service(session),
    )


def get_endings_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> EndingsService:
    return EndingsService(EndingsRepo(session))


@router.get(
    "/me",
    dependencies=[Depends(award_owner_achievements)],
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_profile(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfileResponse:
    """Retrieve full profile including stats for the currently authenticated user."""
    return await service.get_my_profile(user.user_id)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def update_my_profile(
    data: UserProfileUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfileResponse:
    """Update profile attributes (display name, bio, avatar, banner) for current user."""
    return await service.update_profile(user.user_id, data)


@router.post(
    "/me/onboarding",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def complete_my_onboarding(
    data: OnboardingCompleteRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfileResponse:
    """Save first-run wizard answers and mark onboarding complete (idempotent)."""
    return await service.complete_onboarding(user.user_id, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def request_my_account_deletion(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    """Deactivate the account and revoke sessions; it is purged after the grace period unless the user signs back in."""
    await service.request_account_deletion(user.user_id)


@router.get(
    "/me/playthroughs",
    dependencies=[Depends(award_owner_achievements)],
    response_model=list[UserPlaythroughSummary],
    status_code=status.HTTP_200_OK,
)
async def list_my_playthroughs(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
    status: Annotated[str | None, Query()] = None,
) -> list[UserPlaythroughSummary]:
    """List playthrough campaigns belonging to current user."""
    return await service.list_user_playthroughs(user.user_id, status=status)


@router.get(
    "/me/overview",
    response_model=ProfileOverviewResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_overview(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ProfileOverviewService, Depends(get_profile_overview_service)],
) -> ProfileOverviewResponse:
    """Owner-only lifetime stats, weekly activity, continue runs and milestones."""
    return await service.get_overview(user.user_id, datetime.now(UTC))


@router.get(
    "/me/endings",
    response_model=EndingsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_endings(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EndingsService, Depends(get_endings_service)],
) -> EndingsResponse:
    """Owner-only per-story endings progress with locked slots for unfound endings."""
    return await service.get_endings(user.user_id)


@router.get(
    "/me/achievements",
    response_model=list[OwnerAchievementResponse],
    status_code=status.HTTP_200_OK,
)
async def get_my_achievements(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AchievementService, Depends(get_achievement_service)],
) -> list[OwnerAchievementResponse]:
    """Owner-only: all 17 badges with earned dates and progress; awards new ones."""
    return await service.get_owner_achievements(user.user_id, datetime.now(UTC))


@router.get(
    "/{user_id}",
    response_model=UserPublicProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def get_public_profile(
    user_id: uuid.UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserPublicProfileResponse:
    """Retrieve publicly visible profile details and stats for a user."""
    return await service.get_public_profile(user_id)


@router.get(
    "/{user_id}/reviews",
    response_model=list[UserReviewSummary],
    status_code=status.HTTP_200_OK,
)
async def list_user_reviews(
    user_id: uuid.UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserReviewSummary]:
    """List scenario reviews authored by a user."""
    return await service.list_user_reviews(user_id, limit=limit, offset=offset)


@router.get(
    "/{user_id}/achievements",
    response_model=list[PublicAchievementResponse],
    status_code=status.HTTP_200_OK,
)
async def list_user_achievements(
    user_id: uuid.UUID,
    service: Annotated[AchievementService, Depends(get_achievement_service)],
) -> list[PublicAchievementResponse]:
    """Public: earned badges only, no progress; never awards."""
    return await service.get_public_achievements(user_id)
