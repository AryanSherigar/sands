from typing import Annotated
from uuid import UUID

from app.db.pool import get_connection
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.services.dispatch_service import DispatchService
from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection
from strategy_contracts.agents import DispatchView

router = APIRouter(
    prefix="/v1/playthroughs/{playthrough_id}/dispatches", tags=["dispatches"]
)
User = Annotated[CurrentUser, Depends(get_current_user)]


def get_dispatch_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> DispatchService:
    return DispatchService(connection)


Service = Annotated[DispatchService, Depends(get_dispatch_service)]


@router.get("")
async def list_dispatches(
    playthrough_id: UUID,
    user: User,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[DispatchView]:
    """List the owner's spymaster dispatches, newest turn first."""
    return await service.page(playthrough_id, user.user_id, limit)


@router.get("/{rumor_id}")
async def get_dispatch(
    playthrough_id: UUID, rumor_id: str, user: User, service: Service
) -> DispatchView:
    """Read saved prose or current delivery status for one dispatch."""
    return await service.get(playthrough_id, user.user_id, rumor_id)
