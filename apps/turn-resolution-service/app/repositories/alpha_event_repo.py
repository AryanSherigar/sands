"""Server-source alpha event persistence."""

import uuid

from app.db.models.alpha_event import EVENT_SOURCE_SERVER, AlphaEvent
from sqlalchemy.ext.asyncio import AsyncSession


class AlphaEventRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_server_event(
        self,
        user_id: uuid.UUID,
        session_id: str,
        name: str,
        props: dict[str, object],
    ) -> None:
        self.session.add(
            AlphaEvent(
                user_id=user_id,
                session_id=session_id,
                name=name,
                props=props,
                source=EVENT_SOURCE_SERVER,
            )
        )
        await self.session.flush()
