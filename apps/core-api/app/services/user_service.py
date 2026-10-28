"""User domain service managing profile queries, updates, campaigns, and reviews."""

import uuid
from datetime import UTC, datetime

import structlog
from app.config import settings
from app.db.models.user import User
from app.exceptions.alpha_exceptions import AlphaConsentRequiredError
from app.exceptions.user_exceptions import UserNotFoundError
from app.models.user import (
    OnboardingCompleteRequest,
    UserPlaythroughSummary,
    UserProfileResponse,
    UserProfileUpdate,
    UserPublicProfileResponse,
    UserReviewSummary,
    UserStatsResponse,
)
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.user_repo import UserRepo
from app.services.alpha_consent import (
    is_alpha_consent_current,
    log_alpha_consent_recorded,
)

logger = structlog.get_logger()


def _extract_character_info(state: dict[str, object]) -> tuple[str | None, str | None]:
    """Extract character name and archetype from playthrough state setup dictionary."""
    setup = state.get("setup")
    if not isinstance(setup, dict):
        return None, None
    name = setup.get("character_name") or setup.get("name")
    archetype = setup.get("archetype") or setup.get("class") or setup.get("role")
    name_str = str(name) if name is not None else None
    archetype_str = str(archetype) if archetype is not None else None
    return name_str, archetype_str


class UserService:
    """Domain service for user profile data and activity summaries."""

    def __init__(self, user_repo: UserRepo, playthrough_repo: PlaythroughRepo) -> None:
        self.user_repo = user_repo
        self.playthrough_repo = playthrough_repo

    async def _build_profile_response(self, user: User) -> UserProfileResponse:
        stats = UserStatsResponse(**await self.user_repo.get_user_stats(user.user_id))
        return UserProfileResponse(
            user_id=user.user_id,
            display_name=user.display_name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            banner_url=user.banner_url,
            created_at=user.created_at,
            auth_provider_id=user.auth_provider_id,
            voice_output_enabled=user.voice_output_enabled,
            show_mature=user.show_mature,
            preferred_genres=user.preferred_genres,
            onboarding_completed_at=user.onboarding_completed_at,
            alpha_consent_is_current=is_alpha_consent_current(user),
            stats=stats,
        )

    async def get_my_profile(self, user_id: uuid.UUID) -> UserProfileResponse:
        """Retrieve full profile including auth provider ID for current user."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return await self._build_profile_response(user)

    async def record_alpha_consent(
        self, user_id: uuid.UUID, version: str
    ) -> UserProfileResponse:
        """Record acceptance of the current alpha consent text for a returning user."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        if version != settings.alpha_consent_version:
            raise AlphaConsentRequiredError("Consent version is out of date")
        await self.user_repo.record_alpha_consent(user, version)
        log_alpha_consent_recorded(user_id, version)
        return await self._build_profile_response(user)

    async def request_account_deletion(self, user_id: uuid.UUID) -> None:
        """Deactivate the account now; a scheduled purge removes it after the grace period."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        if user.deletion_requested_at is None:
            await self.user_repo.mark_deletion_requested(user, datetime.now(UTC))
        logger.info("account_deletion_requested", user_id=str(user_id))

    async def get_public_profile(self, user_id: uuid.UUID) -> UserPublicProfileResponse:
        """Retrieve publicly visible profile and statistics for any user."""
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.deletion_requested_at is not None:
            raise UserNotFoundError()
        stats_dict = await self.user_repo.get_user_stats(user_id)
        stats = UserStatsResponse(**stats_dict)
        return UserPublicProfileResponse(
            user_id=user.user_id,
            display_name=user.display_name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            banner_url=user.banner_url,
            created_at=user.created_at,
            stats=stats,
        )

    async def update_profile(
        self, user_id: uuid.UUID, data: UserProfileUpdate
    ) -> UserProfileResponse:
        """Update profile fields and return updated profile."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        updated_user = await self.user_repo.update_profile(
            user=user,
            display_name=data.display_name,
            bio=data.bio,
            avatar_url=data.avatar_url,
            banner_url=data.banner_url,
            voice_output_enabled=data.voice_output_enabled,
            show_mature=data.show_mature,
            preferred_genres=data.preferred_genres,
        )
        logger.info("user_profile_updated", user_id=str(user_id))
        return await self._build_profile_response(updated_user)

    async def complete_onboarding(
        self, user_id: uuid.UUID, data: OnboardingCompleteRequest
    ) -> UserProfileResponse:
        """Persist wizard answers once; repeat calls return the profile unchanged."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        if user.onboarding_completed:
            return await self._build_profile_response(user)
        completed_user = await self.user_repo.complete_onboarding(
            user=user,
            completed_at=datetime.now(UTC),
            preferred_genres=data.preferred_genres,
            display_name=data.display_name,
            bio=data.bio,
            avatar_url=data.avatar_url,
            banner_url=data.banner_url,
        )
        logger.info("user_onboarding_completed", user_id=str(user_id))
        return await self._build_profile_response(completed_user)

    async def list_user_playthroughs(
        self, user_id: uuid.UUID, status: str | None = None
    ) -> list[UserPlaythroughSummary]:
        """Fetch all playthroughs for a user with scenario details and character info."""
        records = await self.playthrough_repo.list_by_user_with_scenarios(
            created_by=user_id, status=status
        )
        summaries: list[UserPlaythroughSummary] = []
        for pt, scen in records:
            char_name, char_archetype = _extract_character_info(pt.state)
            summaries.append(
                UserPlaythroughSummary(
                    playthrough_id=pt.playthrough_id,
                    scenario_id=scen.scenario_id,
                    scenario_title=scen.title,
                    scenario_mode=scen.mode,
                    cover_image_url=scen.cover_image_url,
                    turn_count=pt.turn_count,
                    status=pt.status,
                    ended_outcome_tag=pt.ended_outcome_tag,
                    ended_outcome_title=pt.ended_outcome_title,
                    ended_outcome_text=pt.ended_outcome_text,
                    character_name=char_name,
                    character_archetype=char_archetype,
                    created_at=pt.created_at,
                    updated_at=pt.updated_at,
                )
            )
        return summaries

    async def list_user_reviews(
        self, user_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> list[UserReviewSummary]:
        """List reviews written by a user along with scenario titles."""
        reviews = await self.user_repo.list_user_reviews(
            user_id=user_id, limit=limit, offset=offset
        )
        return [
            UserReviewSummary(
                review_id=rev.review_id,
                scenario_id=scen.scenario_id,
                scenario_title=scen.title,
                rating=rev.rating,
                review_text=rev.comment,
                created_at=rev.created_at,
            )
            for rev, scen in reviews
        ]
