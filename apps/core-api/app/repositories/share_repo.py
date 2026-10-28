"""PlaythroughShare data repository for direct database operations."""

import uuid
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.db.models.share import SHARE_PLAYTHROUGH_MODE_CONSTRAINT, PlaythroughShare
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession


class ShareRepo:
    """Repository managing direct SQLAlchemy queries for PlaythroughShare entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def issue(
        self, playthrough_id: uuid.UUID, mode: str, share_token: str
    ) -> PlaythroughShare:
        """Insert the (playthrough, mode) share, or rotate its token in place if
        the existing row is revoked or expired. A still-valid row is returned
        untouched, so concurrent callers converge on the same token."""
        now = datetime.now(UTC)
        insert_stmt = pg_insert(PlaythroughShare).values(
            playthrough_id=playthrough_id,
            mode=mode,
            share_token=share_token,
            expires_at=now + timedelta(days=settings.share_token_expire_days),
        )
        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint=SHARE_PLAYTHROUGH_MODE_CONSTRAINT,
            set_={
                "share_token": insert_stmt.excluded.share_token,
                "expires_at": insert_stmt.excluded.expires_at,
                "revoked_at": None,
            },
            where=or_(
                PlaythroughShare.revoked_at.is_not(None),
                PlaythroughShare.expires_at <= now,
            ),
        ).returning(PlaythroughShare)
        stmt = (
            select(PlaythroughShare)
            .from_statement(upsert_stmt)
            .execution_options(populate_existing=True)
        )
        issued = (await self.session.execute(stmt)).scalars().first()
        return issued or await self._get_required_by_playthrough_and_mode(
            playthrough_id, mode
        )

    async def revoke(self, share: PlaythroughShare) -> None:
        """Mark a share token as revoked, invalidating it immediately."""
        share.revoked_at = datetime.now(UTC)
        await self.session.flush()

    async def get_by_id(self, share_id: uuid.UUID) -> PlaythroughShare | None:
        """Retrieve a share by its primary key."""
        stmt = select(PlaythroughShare).where(PlaythroughShare.share_id == share_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_token(self, share_token: str) -> PlaythroughShare | None:
        """Retrieve a share by its unguessable token."""
        stmt = select(PlaythroughShare).where(
            PlaythroughShare.share_token == share_token
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_playthrough_and_mode(
        self, playthrough_id: uuid.UUID, mode: str
    ) -> PlaythroughShare | None:
        """Retrieve the existing share for a (playthrough, mode) pair, if any."""
        stmt = select(PlaythroughShare).where(
            PlaythroughShare.playthrough_id == playthrough_id,
            PlaythroughShare.mode == mode,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_required_by_playthrough_and_mode(
        self, playthrough_id: uuid.UUID, mode: str
    ) -> PlaythroughShare:
        stmt = (
            select(PlaythroughShare)
            .where(
                PlaythroughShare.playthrough_id == playthrough_id,
                PlaythroughShare.mode == mode,
            )
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().one()
