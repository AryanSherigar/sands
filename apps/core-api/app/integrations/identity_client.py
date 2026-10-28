"""Firebase Auth admin client for Core API.

Only module that deletes identities from the external identity provider.
"""

from __future__ import annotations

import asyncio

import firebase_admin
import structlog
from app.config import settings
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from firebase_admin import exceptions as firebase_exceptions

logger = structlog.get_logger()

EVENT_IDENTITY_ALREADY_DELETED = "identity_already_deleted"
EVENT_IDENTITY_DELETE_SKIPPED = "identity_delete_skipped"


def _ensure_admin_app() -> None:
    if firebase_admin._apps:
        return
    if settings.firebase_credentials_path:
        credential = credentials.Certificate(settings.firebase_credentials_path)
    else:
        credential = credentials.ApplicationDefault()
    firebase_admin.initialize_app(
        credential, options={"projectId": settings.firebase_project_id}
    )


def _delete_identity_sync(auth_provider_id: str) -> None:
    _ensure_admin_app()
    try:
        firebase_auth.delete_user(auth_provider_id)
    except firebase_auth.UserNotFoundError:
        logger.info(EVENT_IDENTITY_ALREADY_DELETED, auth_provider_id=auth_provider_id)


async def delete_identity(auth_provider_id: str) -> None:
    """Delete the Firebase user; a missing user is treated as already deleted.

    Skipped outside production-like environments where no credentials exist.
    """
    is_unconfigured = not settings.firebase_credentials_path
    if settings.environment in ("development", "testing") and is_unconfigured:
        logger.info(EVENT_IDENTITY_DELETE_SKIPPED, auth_provider_id=auth_provider_id)
        return
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _delete_identity_sync, auth_provider_id)
    except firebase_exceptions.FirebaseError:
        logger.exception("identity_delete_failed", auth_provider_id=auth_provider_id)
        raise
