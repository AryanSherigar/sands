from typing import Annotated
from uuid import UUID

from app.db.pool import get_connection
from app.middleware.internal_auth import verify_internal_token
from app.repositories.event_delivery_repo import EventDeliveryRepo
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import AsyncConnection
from strategy_contracts.events import (
    EventNarrativeClaim,
    EventNarrativeClaimInput,
    EventNarrativeCompleteInput,
    EventNarrativeFailInput,
    EventNarrativeView,
)

router = APIRouter(tags=["events-narrative"])
Connection = Annotated[AsyncConnection, Depends(get_connection)]


@router.post(
    "/internal/v1/playthroughs/{playthrough_id}/events/{event_id}/claim",
    dependencies=[Depends(verify_internal_token)],
    response_model=EventNarrativeClaim,
)
async def claim_event_narrative(
    playthrough_id: UUID,
    event_id: str,
    body: EventNarrativeClaimInput,
    connection: Connection,
) -> EventNarrativeClaim:
    repo = EventDeliveryRepo()
    claim = await repo.claim(connection, playthrough_id, event_id, body.claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delivery not claimable",
        )
    return claim


@router.post(
    "/internal/v1/playthroughs/{playthrough_id}/events/{event_id}/complete",
    dependencies=[Depends(verify_internal_token)],
)
async def complete_event_narrative(
    playthrough_id: UUID,
    event_id: str,
    body: EventNarrativeCompleteInput,
    connection: Connection,
) -> dict[str, str]:
    repo = EventDeliveryRepo()
    is_ok = await repo.complete(
        connection, playthrough_id, event_id, body.lease_token, body.narration
    )
    if not is_ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lease expired or invalid",
        )
    return {"status": "completed"}


@router.post(
    "/internal/v1/playthroughs/{playthrough_id}/events/{event_id}/fail",
    dependencies=[Depends(verify_internal_token)],
)
async def fail_event_narrative(
    playthrough_id: UUID,
    event_id: str,
    body: EventNarrativeFailInput,
    connection: Connection,
) -> dict[str, str]:
    repo = EventDeliveryRepo()
    await repo.fail(
        connection, playthrough_id, event_id, body.lease_token, body.error_code
    )
    return {"status": "failed"}


@router.get(
    "/v1/playthroughs/{playthrough_id}/events/{event_id}/narrative",
    response_model=EventNarrativeView,
)
async def get_event_narrative(
    playthrough_id: UUID,
    event_id: str,
    connection: Connection,
) -> EventNarrativeView:
    repo = EventDeliveryRepo()
    row = await repo.get(connection, playthrough_id, event_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event delivery not found",
        )
    return EventNarrativeView(
        event_id=row.event_id,
        status=row.status,
        narration=row.narration,
    )
