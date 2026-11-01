"""Server-side reading of a player's rule-check report.

Used by request_receiver (to derive the turn-log and narrator action text from
the pinned pending check, never from client text) and by rule_check_resolver
(to judge the same report), so both agree on what the player did.
"""

import time

from app.config import settings
from app.models.check_event import CheckReportInput

NO_ANSWER_ACTION_TEXT = "(No answer.)"


def current_time_ms() -> int:
    return time.time_ns() // 1_000_000


def is_armed(pending: dict[str, object]) -> bool:
    """Checks stamped before arming existed carry no flag and count as armed."""
    return pending.get("is_armed", True) is True


def is_late(pending: dict[str, object], report: CheckReportInput, now_ms: int) -> bool:
    if report.is_untimed:
        return False
    issued_at, window_ms = pending.get("issued_at"), pending.get("window_ms")
    if not isinstance(issued_at, int) or not isinstance(window_ms, int):
        return False
    return now_ms - issued_at > window_ms + settings.rule_check_tolerance_ms


def choice_labels(pending: dict[str, object]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for entry in _entries(pending.get("options")):
        labels[str(entry.get("id"))] = str(entry.get("label", ""))
    for entry in _entries(pending.get("variants")):
        labels[str(entry.get("id"))] = str(entry.get("text", ""))
    return labels


def describe_action(
    pending: dict[str, object], report: CheckReportInput, now_ms: int
) -> str:
    if report.timed_out or is_late(pending, report, now_ms):
        return NO_ANSWER_ACTION_TEXT
    label = choice_labels(pending).get(report.choice_id or "")
    return label if label else NO_ANSWER_ACTION_TEXT


def _entries(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]
