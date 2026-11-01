"""Read-only view of the scenario tools pinned into a playthrough snapshot."""

KNOWN_TOOLS: frozenset[str] = frozenset(
    {"rule_checks", "rule_sheet", "status_hud", "atmosphere", "composure"}
)


def enabled_tools(snapshot: dict[str, object]) -> list[str]:
    listed = snapshot.get("enabled_tools")
    if not isinstance(listed, list):
        return []
    return [key for key in listed if isinstance(key, str) and key in KNOWN_TOOLS]


def is_enabled(snapshot: dict[str, object], tool_key: str) -> bool:
    return tool_key in enabled_tools(snapshot)
