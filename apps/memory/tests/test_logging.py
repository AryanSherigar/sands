"""Tests for app.logging's redaction processor."""

import json

import pytest
import structlog
from app.logging import REDACTION_PLACEHOLDER, configure_logging

CANARY = "super-secret-turn-payload"


@pytest.fixture(autouse=True)
def _reset_structlog_config():
    yield
    structlog.reset_defaults()


def test_redacted_keys_are_scrubbed_and_other_keys_survive(capsys) -> None:
    configure_logging("INFO")
    logger = structlog.get_logger()
    logger.info(
        "test_event",
        text=CANARY,
        content=CANARY,
        action_text=CANARY,
        narration_text=CANARY,
        raw_output=CANARY,
        api_key=CANARY,
        turn_id="abc-123",
    )

    captured = capsys.readouterr()
    assert CANARY not in captured.out

    event = json.loads(captured.out.strip().splitlines()[-1])
    assert event["text"] == REDACTION_PLACEHOLDER
    assert event["content"] == REDACTION_PLACEHOLDER
    assert event["action_text"] == REDACTION_PLACEHOLDER
    assert event["narration_text"] == REDACTION_PLACEHOLDER
    assert event["raw_output"] == REDACTION_PLACEHOLDER
    assert event["api_key"] == REDACTION_PLACEHOLDER
    assert event["turn_id"] == "abc-123"
