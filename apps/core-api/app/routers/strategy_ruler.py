"""FastAPI router for strategy ruler customization endpoints."""

from typing import Annotated

from app.db.connection import get_db_session
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.models.strategy_ruler import RulerBackstoryRequest, RulerBackstoryResponse
from app.repositories.scenario_repo import ScenarioRepo
from app.services import ruler_backstory_service
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Strategy"])


@router.post(
    "/v1/strategy/ruler-backstory",
    response_model=RulerBackstoryResponse,
    status_code=status.HTTP_200_OK,
)
async def draft_ruler_backstory(
    req: RulerBackstoryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
    quota_service: Annotated[QuotaService, Depends(get_quota_service)],
) -> RulerBackstoryResponse:
    """Draft an evocative coronation backstory for a customized strategy ruler."""
    story = await ruler_backstory_service.draft_ruler_backstory(
        req, current_user, ScenarioRepo(session), quota_service
    )
    return RulerBackstoryResponse(backstory=story)
