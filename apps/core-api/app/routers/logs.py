"""FastAPI router for client-side (frontend) log ingestion."""

from typing import Annotated

from app.config import settings
from app.db.models.user import User
from app.middleware.auth import get_optional_current_user
from app.middleware.body_limit import limit_body_size
from app.models.logs import ClientLogBatch
from app.services.log_ingestion_service import LogIngestionService
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/v1/logs", tags=["logs"])


def get_log_ingestion_service() -> LogIngestionService:
    return LogIngestionService()


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_body_size(settings.client_log_max_body_bytes))],
)
async def ingest_client_logs(
    batch: ClientLogBatch,
    user: Annotated[User | None, Depends(get_optional_current_user)],
    service: Annotated[LogIngestionService, Depends(get_log_ingestion_service)],
) -> None:
    """Accept a batch of client-side log events. Auth optional (pre-login errors too)."""
    service.ingest_batch(batch, user_id=user.user_id if user else None)
