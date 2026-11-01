"""The per-request ingest log line carries what evaluation needs to size latency."""

from uuid import uuid4

import pytest
import structlog
from app.services import ingest_service
from app.services.ingest_service import IngestService
from psycopg import AsyncConnection
from tests.services.ingest_helpers import (
    build_request,
    register_item,
    seed_template_world,
)


async def test_ingest_request_log_reports_duration_and_counts(
    db_connection: AsyncConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = await seed_template_world(db_connection)
    request = build_request(uuid4(), register_item(world.scenario_id))

    with structlog.testing.capture_logs() as logs:
        monkeypatch.setattr(ingest_service, "logger", structlog.get_logger())
        await IngestService(db_connection).ingest_items(request)

    [event] = [log for log in logs if log["event"] == "ingest_items_applied"]
    assert isinstance(event["duration_ms"], int) and event["duration_ms"] >= 0
    assert (event["item_count"], event["applied_count"]) == (1, 1)
