"""User data repository (mirrors core-api's schema, read-only in TRS)."""

import uuid

from app.db.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepo:
    """Repository managing read-only SQLAlchemy queries for User."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by unique user UUID."""
        stmt = select(User).where(User.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_alpha_consent_version(self, user_id: uuid.UUID) -> str | None:
        """Fetch the consent version the user last accepted, if any."""
        stmt = select(User.alpha_consent_version).where(User.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
