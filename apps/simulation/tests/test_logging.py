import json

import pytest
import structlog
from app.logging import REDACTION_PLACEHOLDER, SERVICE_NAME, configure_logging

CANARY = "super-secret"


@pytest.fixture(autouse=True)
def _reset_structlog_config():
    yield
    structlog.reset_defaults()


def test_api_key_is_redacted_and_other_fields_survive(capsys) -> None:
    configure_logging("INFO")
    structlog.get_logger().info("test_event", api_key=CANARY, turn_id="abc-123")
    captured = capsys.readouterr()
    assert CANARY not in captured.out
    event = json.loads(captured.out.strip().splitlines()[-1])
    assert event["api_key"] == REDACTION_PLACEHOLDER
    assert event["turn_id"] == "abc-123"
    assert event["service"] == SERVICE_NAME
