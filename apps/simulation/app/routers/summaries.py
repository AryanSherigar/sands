from typing import Annotated
from uuid import UUID

from app.db.pool import get_connection
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.services.summary_service import SummaryService
from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection
from strategy_contracts.summary import SummaryPage, SummaryView

router = APIRouter(
    prefix="/v1/playthroughs/{playthrough_id}/summaries", tags=["summaries"]
)
User = Annotated[CurrentUser, Depends(get_current_user)]


def get_summary_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> SummaryService:
    return SummaryService(connection)


Service = Annotated[SummaryService, Depends(get_summary_service)]


@router.get("")
async def list_summaries(
    playthrough_id: UUID,
    user: User,
    service: Service,
    after_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SummaryPage:
    """List the owner's durable chronicles with an opaque scoped cursor."""
    return await service.page(playthrough_id, user.user_id, after_id, limit)


@router.get("/{summary_id}")
async def get_summary(
    playthrough_id: UUID, summary_id: UUID, user: User, service: Service
) -> SummaryView:
    """Read saved prose or current delivery status without changing world state."""
    return await service.get(playthrough_id, user.user_id, summary_id)
