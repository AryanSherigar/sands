import uuid

import structlog
from app.config import settings
from app.db.models.user import User
from app.exceptions.alpha_exceptions import AlphaConsentRequiredError
from app.logging_config import log_audit_event

logger = structlog.get_logger()

EVENT_ALPHA_CONSENT_RECORDED = "alpha_consent_recorded"


def log_alpha_consent_recorded(user_id: uuid.UUID, version: str) -> None:
    log_audit_event(
        logger,
        EVENT_ALPHA_CONSENT_RECORDED,
        user_id=str(user_id),
        consent_version=version,
    )


def is_alpha_consent_current(user: User) -> bool:
    if not settings.is_alpha_mode:
        return True
    return user.alpha_consent_version == settings.alpha_consent_version


def require_alpha_collection_consent(user: User) -> None:
    """Data collection exists only in alpha mode, for a user on the current consent."""
    if not settings.is_alpha_mode or not is_alpha_consent_current(user):
        raise AlphaConsentRequiredError()
