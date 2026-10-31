"""Registry of optional scenario tools (docs/adr/016-optional-scenario-tools.md)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.db.models.scenario import Scenario
from app.exceptions.tool_exceptions import UnknownToolError


@dataclass(frozen=True)
class ToolDefinition:
    key: str
    display_name: str
    summary: str
    requires: tuple[str, ...] = ()


TOOLS: dict[str, ToolDefinition] = {
    "rule_checks": ToolDefinition(
        "rule_checks", "Rule checks", "Timed prompts and recall tests"
    ),
    "rule_sheet": ToolDefinition(
        "rule_sheet", "Rules & clipboard", "A rule sheet that changes as you play"
    ),
    "status_hud": ToolDefinition(
        "status_hud", "Status HUD", "Clock, meters and tension display"
    ),
    "atmosphere": ToolDefinition(
        "atmosphere",
        "Atmosphere",
        "Cues, audio and reader effects",
        ("status_hud",),
    ),
    "composure": ToolDefinition("composure", "Composure minigame", "Rhythm challenges"),
}


def validate_known(enabled: Sequence[str]) -> None:
    unknown = [key for key in enabled if key not in TOOLS]
    if unknown:
        raise UnknownToolError(unknown)


def _requirements_of(key: str) -> set[str]:
    pending = list(TOOLS[key].requires)
    required: set[str] = set()
    while pending:
        current = pending.pop()
        if current not in required:
            required.add(current)
            pending.extend(TOOLS[current].requires)
    return required


def close_over_requires(enabled: Sequence[str]) -> tuple[list[str], list[str]]:
    """Returns (closed list in registry order, keys that were auto-added)."""
    validate_known(enabled)
    requested = set(enabled)
    closed = set(requested)
    for key in requested:
        closed |= _requirements_of(key)
    ordered = [key for key in TOOLS if key in closed]
    auto_added = [key for key in ordered if key not in requested]
    return ordered, auto_added


def dependents_of(key: str, enabled: Sequence[str]) -> list[str]:
    return [
        other for other in enabled if other in TOOLS and key in _requirements_of(other)
    ]


STATE_SCHEMA_EXTENSION_KEY = "_state_schema_extension"

SnapshotContributor = Callable[[Scenario, Sequence[object]], dict[str, object]]

_SNAPSHOT_CONTRIBUTORS: dict[str, SnapshotContributor] = {}


def register_snapshot_contributor(
    tool_key: str, contributor: SnapshotContributor
) -> None:
    _SNAPSHOT_CONTRIBUTORS[tool_key] = contributor


def unregister_snapshot_contributor(tool_key: str) -> None:
    _SNAPSHOT_CONTRIBUTORS.pop(tool_key, None)


def contribute_snapshot(
    tool_key: str, scenario: Scenario, rows: Sequence[object]
) -> dict[str, object]:
    contributor = _SNAPSHOT_CONTRIBUTORS.get(tool_key)
    if contributor is None:
        return {}
    return contributor(scenario, rows)
