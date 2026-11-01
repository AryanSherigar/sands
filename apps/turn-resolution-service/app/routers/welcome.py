import uuid
from typing import Annotated

from app.db.connection import get_db_session
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.welcome_service import generate_welcome_closing
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/voice", tags=["Welcome tape"])


@router.post("/welcome/{playthrough_id}")
async def welcome_closing(
    playthrough_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    quota_service: Annotated[QuotaService, Depends(get_quota_service)],
) -> Response:
    """Return transient Katie closing audio for an owned, unstarted welcome run."""
    content = await generate_welcome_closing(
        playthrough_id, current_user.user_id, session, quota_service
    )
    return Response(
        content=content, media_type="audio/wav", headers={"Cache-Control": "no-store"}
    )
