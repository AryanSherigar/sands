from typing import Annotated
from uuid import UUID

from app.integrations.simulation_client import SimulationArtClient
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.strategy_art_service import generate_art
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from strategy_contracts.art import (
    ART_ITEM_ID_PATTERN,
    MAX_ART_ITEM_ID_CHARS,
    ArtKind,
    ArtView,
)

router = APIRouter(
    prefix="/v1/strategy/playthroughs",
    tags=["strategy-art"],
)


class StrategyArtInput(BaseModel):
    kind: ArtKind
    item_id: str = Field(
        min_length=1, max_length=MAX_ART_ITEM_ID_CHARS, pattern=ART_ITEM_ID_PATTERN
    )
    client_request_id: UUID


@router.post("/{playthrough_id}/art")
async def request_strategy_art(
    playthrough_id: UUID,
    request: StrategyArtInput,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
    authorization: Annotated[str | None, Header()] = None,
    dev_user_id: Annotated[str | None, Header(alias="X-Dev-User-Id")] = None,
) -> ArtView:
    """Return an owned item's saved art, generating it once on first request."""
    client = SimulationArtClient(authorization, dev_user_id)
    return await generate_art(
        playthrough_id,
        request.kind,
        request.item_id,
        request.client_request_id,
        client,
        user.user_id,
        quota,
    )
