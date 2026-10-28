"""Render a scenario's authored opening scene for one playthrough."""

PLAYER_NAME_TOKEN = "{player_name}"
FALLBACK_OPENING_NAME = "Adventurer"


def render_opening_scene(text: str | None, character_name: str) -> str | None:
    """Replaces `{player_name}` only; other braces are left as authored."""
    if text is None or not text.strip():
        return None
    name = character_name.strip() or FALLBACK_OPENING_NAME
    return text.replace(PLAYER_NAME_TOKEN, name)
