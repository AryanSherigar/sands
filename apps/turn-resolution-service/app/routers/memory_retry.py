"""Player-facing "Retry memory" endpoint."""

import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.models.memory_retry import MemoryRetryResponse
from app.services import memory_retry_service
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/playthroughs", tags=["Memory"])


@router.post("/{playthrough_id}/memory/retry", response_model=MemoryRetryResponse)
async def retry_memory(
    playthrough_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MemoryRetryResponse:
    """Retry delayed story memory for a playthrough the caller participates in.

    Redelivers pending memory rows, asks memory to retry failed work, and returns
    the reasons still holding. Never replays a turn."""
    return await memory_retry_service.retry_memory(
        session, playthrough_id, current_user.user_id
    )
