"""Ownership check for every /v1/playthroughs/{playthrough_id}/... route."""

from typing import Annotated
from uuid import UUID

from app.db.pool import get_connection
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.persistence import PlaythroughRow
from app.repositories import playthrough_repo
from fastapi import Depends
from psycopg import AsyncConnection


class PlaythroughAccessService:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def require_owned_playthrough(
        self, playthrough_id: UUID, user_id: UUID
    ) -> PlaythroughRow:
        playthrough = await playthrough_repo.get_playthrough(
            self._connection, playthrough_id
        )
        if playthrough is None or playthrough.owner_user_id != user_id:
            raise PlaythroughNotFoundError()
        return playthrough


async def get_owned_playthrough(
    playthrough_id: UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> PlaythroughRow:
    service = PlaythroughAccessService(connection)
    return await service.require_owned_playthrough(playthrough_id, user.user_id)
