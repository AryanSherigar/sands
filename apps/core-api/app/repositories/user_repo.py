"""User repository for database operations."""

import uuid
from datetime import datetime, timezone

from app.db.models.playthrough import Playthrough
from app.db.models.review import ScenarioReview
from app.db.models.scenario import PUBLIC_VISIBILITY, Scenario
from app.db.models.user import User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepo:
    """Repository handling database queries for User entities and profile stats."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_auth_provider_id(self, auth_provider_id: str) -> User | None:
        """Fetch user by external auth provider ID."""
        stmt = select(User).where(User.auth_provider_id == auth_provider_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by unique user UUID."""
        stmt = select(User).where(User.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(
        self,
        auth_provider_id: str,
        display_name: str,
        alpha_consent_version: str | None = None,
    ) -> User:
        """Persist a newly registered user account."""
        user = User(
            auth_provider_id=auth_provider_id,
            display_name=display_name,
        )
        if alpha_consent_version is not None:
            user.alpha_consent_version = alpha_consent_version
            user.alpha_consented_at = datetime.now(timezone.utc)
        self.session.add(user)
        await self.session.flush()
        return user

    async def create_with_id(
        self, user_id: uuid.UUID, auth_provider_id: str, display_name: str
    ) -> User:
        """Persist a user with a caller-supplied UUID, for dev-mode
        auto-provisioning where the UUID comes from a trusted header rather
        than being DB-generated."""
        user = User(
            user_id=user_id,
            auth_provider_id=auth_provider_id,
            display_name=display_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def record_alpha_consent(self, user: User, version: str) -> User:
        """Store the consent version a user accepted and when."""
        user.alpha_consent_version = version
        user.alpha_consented_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def update(self, user: User) -> User:
        """Flush changes to an existing user entity."""
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def mark_deletion_requested(self, user: User, requested_at: datetime) -> User:
        """Flag the account for deletion and revoke every issued token."""
        user.deletion_requested_at = requested_at
        user.token_version += 1
        user.current_refresh_jti = None
        user.previous_refresh_jti = None
        return await self.update(user)

    async def clear_deletion_request(self, user: User) -> User:
        """Cancel a pending deletion, restoring the account."""
        user.deletion_requested_at = None
        return await self.update(user)

    async def mark_suspended(self, user: User, suspended_at: datetime) -> User:
        """Suspend the account and revoke every issued token."""
        user.alpha_suspended_at = suspended_at
        user.token_version += 1
        user.current_refresh_jti = None
        user.previous_refresh_jti = None
        return await self.update(user)

    async def clear_suspension(self, user: User) -> User:
        """Lift a suspension; the user signs in again to get fresh tokens."""
        user.alpha_suspended_at = None
        return await self.update(user)

    async def update_profile(
        self,
        user: User,
        display_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
        banner_url: str | None = None,
        voice_output_enabled: bool | None = None,
        show_mature: bool | None = None,
        preferred_genres: list[str] | None = None,
    ) -> User:
        """Update editable profile fields for a user."""
        if preferred_genres is not None:
            user.preferred_genres = preferred_genres
        if display_name is not None:
            user.display_name = display_name
        if bio is not None:
            user.bio = bio
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if banner_url is not None:
            user.banner_url = banner_url
        if voice_output_enabled is not None:
            user.voice_output_enabled = voice_output_enabled
        if show_mature is not None:
            user.show_mature = show_mature
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def complete_onboarding(
        self,
        user: User,
        completed_at: datetime,
        preferred_genres: list[str],
        display_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
        banner_url: str | None = None,
    ) -> User:
        """Apply wizard answers and stamp onboarding completion in one flush."""
        user.preferred_genres = preferred_genres
        user.onboarding_completed_at = completed_at
        return await self.update_profile(
            user,
            display_name=display_name,
            bio=bio,
            avatar_url=avatar_url,
            banner_url=banner_url,
        )

    async def get_player_stats(self, user_id: uuid.UUID) -> tuple[int, int, int]:
        """Aggregate campaigns played, victories won, and total turns taken."""
        stmt = select(
            func.count(Playthrough.playthrough_id),
            func.count(Playthrough.playthrough_id).filter(
                Playthrough.ended_outcome_tag == "win"
            ),
            func.coalesce(func.sum(Playthrough.turn_count), 0),
        ).where(
            Playthrough.created_by == user_id,
            Playthrough.is_playtest.is_(False),
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return 0, 0, 0
        return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)

    async def get_creator_stats(self, user_id: uuid.UUID) -> tuple[int, int]:
        """Aggregate published scenarios authored and total plays received."""
        stmt = select(
            func.count(Scenario.scenario_id),
            func.coalesce(func.sum(Scenario.play_count), 0),
        ).where(
            Scenario.creator_id == user_id,
            Scenario.status == "published",
            Scenario.visibility == PUBLIC_VISIBILITY,
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return 0, 0
        return int(row[0] or 0), int(row[1] or 0)

    async def get_user_stats(self, user_id: uuid.UUID) -> dict[str, int]:
        """Fetch combined player and creator statistics."""
        campaigns_count, victories_count, total_turns = await self.get_player_stats(
            user_id
        )
        scenarios_count, total_plays = await self.get_creator_stats(user_id)
        return {
            "campaigns_played_count": campaigns_count,
            "victories_count": victories_count,
            "total_turns_taken": total_turns,
            "scenarios_authored_count": scenarios_count,
            "total_plays_received": total_plays,
        }

    async def list_user_reviews(
        self, user_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> list[tuple[ScenarioReview, Scenario]]:
        """Fetch scenario reviews authored by user along with scenario metadata."""
        stmt = (
            select(ScenarioReview, Scenario)
            .join(Scenario, ScenarioReview.scenario_id == Scenario.scenario_id)
            .where(ScenarioReview.user_id == user_id)
            .order_by(ScenarioReview.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.all())
