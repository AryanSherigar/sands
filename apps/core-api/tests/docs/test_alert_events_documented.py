"""The alert metric filters in the docs must name events the code really emits.

A renamed event would silently flatline its log-based metric, so the filter
strings in the docs are checked against the string constants in the services.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SERVICE_SOURCE_DIRS = (
    REPO_ROOT / "apps" / "core-api" / "app",
    REPO_ROOT / "apps" / "turn-resolution-service" / "app",
)
LOGGING_DOC = REPO_ROOT / "docs" / "logging.md"
BACKTICKED = re.compile(r"`([a-z_]+)`")
LOGGING_SECTION = "## Alert metrics"
EVENT_COLUMN_INDEX = 1


def section_rows(text: str, heading: str) -> list[list[str]]:
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    cells = [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]
    return [row for row in cells[2:] if row]


def events_in_column(rows: list[list[str]], index: int) -> set[str]:
    return {event for row in rows for event in BACKTICKED.findall(row[index])}


def source_text() -> str:
    return "\n".join(
        path.read_text()
        for directory in SERVICE_SOURCE_DIRS
        for path in directory.rglob("*.py")
    )


def documented_events() -> list[tuple[str, str]]:
    logging_rows = section_rows(LOGGING_DOC.read_text(), LOGGING_SECTION)
    return [
        ("docs/logging.md", event)
        for event in sorted(events_in_column(logging_rows, EVENT_COLUMN_INDEX))
    ]


def test_the_docs_list_at_least_the_expected_alert_events() -> None:
    events = {event for _, event in documented_events()}

    assert {
        "openai_stream_error",
        "turn_metrics_failed",
        "global_cap_reached",
    } <= events


@pytest.mark.parametrize(("document", "event"), documented_events())
def test_documented_event_is_emitted_by_the_code(document: str, event: str) -> None:
    assert f'"{event}"' in source_text(), f"{document} names {event} but no code does"
