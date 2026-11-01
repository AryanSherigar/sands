from typing import Annotated
from uuid import UUID

from app.middleware.auth import get_current_user
from app.models.api_commands import AcceptCommandRequest, CommandPage
from app.models.api_orders import CheckCommandRequest, OrderCheckResponse
from app.models.auth import CurrentUser
from app.models.battle_progress import MutationResponse, OperationGuard
from app.services.api_dependencies import get_command_service
from app.services.command_service import CommandService
from fastapi import APIRouter, Depends, Path, Query

router = APIRouter(
    prefix="/v1/playthroughs/{playthrough_id}/commands", tags=["commands"]
)
User = Annotated[CurrentUser, Depends(get_current_user)]
Commands = Annotated[CommandService, Depends(get_command_service)]


@router.post("")
async def accept_command(
    playthrough_id: UUID,
    request: AcceptCommandRequest,
    user: User,
    service: Commands,
) -> MutationResponse:
    """Accept a typed command with one operation identity and optimistic cursor."""
    return await service.accept_request(playthrough_id, user.user_id, request)


@router.post("/check")
async def check_command(
    playthrough_id: UUID,
    request: CheckCommandRequest,
    user: User,
    service: Commands,
) -> OrderCheckResponse:
    """Dry-run an order: a flag and reason when it would be refused, nothing charged or stored."""
    return await service.check(playthrough_id, user.user_id, request.command)


@router.post("/{command_id}/cancel")
async def cancel_command(
    playthrough_id: UUID,
    command_id: Annotated[str, Path(max_length=256)],
    request: OperationGuard,
    user: User,
    service: Commands,
) -> MutationResponse:
    """Remove a queued planning order before End Turn and refund its command points."""
    return await service.cancel(playthrough_id, user.user_id, request, command_id)


@router.get("")
async def list_commands(
    playthrough_id: UUID,
    user: User,
    service: Commands,
    after_id: Annotated[str, Query(max_length=256)] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> CommandPage:
    """List own commands in durable acceptance order; the cursor is a command ID."""
    return await service.command_page(playthrough_id, user.user_id, after_id, limit)
