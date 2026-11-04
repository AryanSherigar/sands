from typing import Annotated
from uuid import UUID

from app.integrations.simulation_client import SimulationEventNarrativeClient
from app.middleware.auth import get_current_user
from app.models.auth import CurrentUser
from app.services.rate_limit.quota_service import QuotaService, get_quota_service
from app.services.strategy_event_service import narrate_strategy_event
from fastapi import APIRouter, Depends, Header
from strategy_contracts.events import EventNarrativePayload

router = APIRouter(
    prefix="/v1/strategy/playthroughs",
    tags=["strategy-events"],
)


@router.post(
    "/{playthrough_id}/events/{event_id}/narrate",
    response_model=EventNarrativePayload | None,
)
async def narrate_strategy_event_endpoint(
    playthrough_id: UUID,
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
    authorization: Annotated[str | None, Header()] = None,
    dev_user_id: Annotated[str | None, Header(alias="X-Dev-User-Id")] = None,
) -> EventNarrativePayload | None:
    client = SimulationEventNarrativeClient(authorization, dev_user_id)
    return await narrate_strategy_event(
        playthrough_id, event_id, client, user.user_id, quota
    )
