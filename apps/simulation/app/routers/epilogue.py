from typing import Annotated
from uuid import UUID

from app.db.pool import get_connection
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.services.epilogue_service import EpilogueService
from fastapi import APIRouter, Depends
from psycopg import AsyncConnection
from strategy_contracts.epilogue import EpilogueView

router = APIRouter(
    prefix="/v1/playthroughs/{playthrough_id}/epilogue", tags=["epilogue"]
)
User = Annotated[CurrentUser, Depends(get_current_user)]


def get_epilogue_service(
    connection: Annotated[AsyncConnection, Depends(get_connection)],
) -> EpilogueService:
    return EpilogueService(connection)


Service = Annotated[EpilogueService, Depends(get_epilogue_service)]


@router.get("")
async def get_epilogue(
    playthrough_id: UUID, user: User, service: Service
) -> EpilogueView:
    """Read the saved closing entry or its delivery status once the game has ended."""
    return await service.get(playthrough_id, user.user_id)
