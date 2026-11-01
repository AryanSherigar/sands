import asyncio
from uuid import UUID

import httpx
import structlog
from app.config import settings
from app.integrations.simulation_client import SimulationArtClient
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaReservation, QuotaService
from app.turn.steps.strategy_art_generator import generate_strategy_art
from strategy_contracts.art import (
    ArtClaim,
    ArtCompleteInput,
    ArtFailInput,
    ArtKind,
    ArtView,
)

logger = structlog.get_logger()

COMPLETE_ATTEMPTS = 3
COMPLETE_RETRY_DELAY_SECONDS = 0.1
UNAVAILABLE_CODE = "provider_unavailable"


def _failed_view(kind: ArtKind, item_id: str) -> ArtView:
    return ArtView(
        kind=kind,
        item_id=item_id,
        status="failed",
        error_code=UNAVAILABLE_CODE,
        is_retryable=True,
    )


async def _refund(reservation: QuotaReservation | None) -> None:
    if reservation is not None:
        await reservation.refund()


async def _claim_or_refund(
    client: SimulationArtClient,
    identity: UUID,
    kind: ArtKind,
    item_id: str,
    claim_id: UUID,
    reservation: QuotaReservation | None,
) -> ArtClaim:
    try:
        return await client.claim(identity, kind, item_id, claim_id)
    except BaseException:
        await _refund(reservation)
        raise


async def _complete_with_retry(
    client: SimulationArtClient,
    identity: UUID,
    kind: ArtKind,
    item_id: str,
    request: ArtCompleteInput,
) -> ArtView:
    for attempt in range(COMPLETE_ATTEMPTS):
        try:
            return await client.complete(identity, kind, item_id, request)
        except httpx.TransportError:
            if attempt == COMPLETE_ATTEMPTS - 1:
                raise
            await asyncio.sleep(COMPLETE_RETRY_DELAY_SECONDS * (attempt + 1))
    raise AssertionError("unreachable")


async def _record_failure(
    client: SimulationArtClient,
    identity: UUID,
    kind: ArtKind,
    item_id: str,
    lease_token: UUID,
) -> None:
    try:
        await client.fail(
            identity,
            kind,
            item_id,
            ArtFailInput(lease_token=lease_token, error_code=UNAVAILABLE_CODE),
        )
    except httpx.HTTPError:
        logger.warning("strategy_art_failure_callback_failed", kind=kind)


async def _generate_and_save(
    client: SimulationArtClient,
    identity: UUID,
    claim: ArtClaim,
    reservation: QuotaReservation | None,
) -> ArtView:
    kind, item_id = claim.art.kind, claim.art.item_id
    assert claim.briefing is not None and claim.lease_token is not None
    art_url = await generate_strategy_art(
        claim.briefing, settings.image_generation_timeout_seconds
    )
    try:
        if art_url is None:
            raise httpx.ConnectError("generation failed")
        request = ArtCompleteInput(lease_token=claim.lease_token, art_url=art_url)
        return await _complete_with_retry(client, identity, kind, item_id, request)
    except httpx.HTTPError:
        await _record_failure(client, identity, kind, item_id, claim.lease_token)
        await _refund(reservation)
        return _failed_view(kind, item_id)


async def generate_art(
    identity: UUID,
    kind: ArtKind,
    item_id: str,
    claim_id: UUID,
    client: SimulationArtClient,
    user_id: UUID,
    quota: QuotaService,
) -> ArtView:
    """Return saved art, or claim a lease, generate once and save the URL."""
    reservation = await quota.reserve(QuotaFeature.STRATEGY_ART, user_id)
    claim = await _claim_or_refund(
        client, identity, kind, item_id, claim_id, reservation
    )
    if claim.art.status == "completed" or claim.lease_token is None:
        await _refund(reservation)
        return claim.art
    return await _generate_and_save(client, identity, claim, reservation)
