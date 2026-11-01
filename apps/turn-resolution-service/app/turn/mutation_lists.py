"""Read rule for a condition's or minigame outcome's mutations."""


def mutations_from(listed: object, legacy_single: object) -> list[dict[str, object]]:
    """The list wins; pinned old snapshots only have the single legacy key."""
    if isinstance(listed, list) and listed:
        return [item for item in listed if isinstance(item, dict)]
    return [legacy_single] if isinstance(legacy_single, dict) else []
