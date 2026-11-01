"""Size cap on a player's free-typed turn action."""

from app.models.turn import ActionTextLimitResult


def truncate_action_text(text: str, max_chars: int) -> ActionTextLimitResult:
    stripped_text = text.strip()
    original_length = len(stripped_text)
    is_truncated = original_length > max_chars
    return ActionTextLimitResult(
        text=stripped_text[:max_chars] if is_truncated else stripped_text,
        original_length=original_length,
        is_truncated=is_truncated,
    )
