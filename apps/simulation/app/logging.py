"""structlog JSON logging configuration for the simulation service."""

import logging

import structlog

from app.config import get_settings

SERVICE_NAME = "simulation"

REDACTED_FIELD_NAMES: frozenset[str] = frozenset({"api_key"})
REDACTION_PLACEHOLDER = "[REDACTED]"

_LEVEL_NAME_TO_NUMERIC: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def redact_sensitive_fields(
    logger: object, method_name: str, event_dict: dict[str, object]
) -> dict[str, object]:
    for key in event_dict:
        if key.lower() in REDACTED_FIELD_NAMES:
            event_dict[key] = REDACTION_PLACEHOLDER
    return event_dict


def _add_static_fields(
    logger: object, method_name: str, event_dict: dict[str, object]
) -> dict[str, object]:
    event_dict["service"] = SERVICE_NAME
    event_dict["environment"] = get_settings().environment
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog once, at process start, before the FastAPI app is built."""
    numeric_level = _LEVEL_NAME_TO_NUMERIC.get(log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _add_static_fields,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            redact_sensitive_fields,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
