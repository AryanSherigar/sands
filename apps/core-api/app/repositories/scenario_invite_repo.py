"""Repository for single-use scenario invite links."""

import uuid
from datetime import datetime

from app.db.models.scenario_invite import ScenarioInvite
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class ScenarioInviteRepo:
    """Direct SQLAlchemy queries for ScenarioInvite rows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, invite: ScenarioInvite) -> ScenarioInvite:
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def get_by_token_hash(self, token_hash: str) -> ScenarioInvite | None:
        stmt = select(ScenarioInvite).where(ScenarioInvite.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()

    async def consume(self, token_hash: str, user_id: uuid.UUID, now: datetime) -> bool:
        """Burns the token if it is unused and unexpired; one statement, so two
        simultaneous takers cannot both win."""
        stmt = (
            update(ScenarioInvite)
            .where(
                ScenarioInvite.token_hash == token_hash,
                ScenarioInvite.consumed_at.is_(None),
                ScenarioInvite.expires_at > now,
            )
            .values(consumed_at=now, consumed_by=user_id)
            .returning(ScenarioInvite.invite_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None
