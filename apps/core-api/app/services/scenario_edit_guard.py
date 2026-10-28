"""Authored content is read-only while a publish is in flight (ADR-14)."""

from datetime import datetime

from app.db.models.scenario import Scenario
from app.exceptions.scenario_exceptions import (
    ScenarioAlreadyPublishingError,
    ScenarioEditConflictError,
)

EDIT_WHILE_PUBLISHING_MESSAGE = "Cannot edit a scenario while it is being published"


def ensure_not_publishing(scenario: Scenario) -> None:
    if scenario.status == "publishing":
        raise ScenarioAlreadyPublishingError(EDIT_WHILE_PUBLISHING_MESSAGE)


def ensure_not_stale(
    scenario: Scenario, expected_content_edited_at: datetime | None
) -> None:
    """A write that names the edit stamp it was based on fails when the story has
    changed since; a write that names none is applied as before."""
    if (
        expected_content_edited_at is not None
        and scenario.content_edited_at != expected_content_edited_at
    ):
        raise ScenarioEditConflictError()
