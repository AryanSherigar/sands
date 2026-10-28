"""Validation of the guided-creation keys inside Scenario.world_data."""

from app.models.lore_document import LoreDocument

KEY_PREMISE = "premise"
KEY_PREMISE_DOCUMENT = "premiseDocument"
KEY_WORLD_LORE = "worldLore"
KEY_WORLD_LORE_DOCUMENT = "worldLoreDocument"
KEY_OPENING_DOCUMENT = "openingDocument"
KEY_ALWAYS_REMEMBER = "alwaysRemember"
LORE_DOCUMENT_KEYS = (
    KEY_PREMISE_DOCUMENT,
    KEY_WORLD_LORE_DOCUMENT,
    KEY_OPENING_DOCUMENT,
)
MAX_ALWAYS_REMEMBER_LINES = 30
MAX_ALWAYS_REMEMBER_LINE_LENGTH = 300


def _validate_always_remember(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not all(isinstance(line, str) for line in value):
        raise ValueError(f"{KEY_ALWAYS_REMEMBER} must be a list of strings")
    if len(value) > MAX_ALWAYS_REMEMBER_LINES:
        raise ValueError(
            f"{KEY_ALWAYS_REMEMBER} allows at most {MAX_ALWAYS_REMEMBER_LINES} lines"
        )
    if any(len(line) > MAX_ALWAYS_REMEMBER_LINE_LENGTH for line in value):
        raise ValueError(
            f"{KEY_ALWAYS_REMEMBER} lines are limited to "
            f"{MAX_ALWAYS_REMEMBER_LINE_LENGTH} characters"
        )


def validate_world_data_documents(
    world_data: dict[str, object] | None,
) -> dict[str, object] | None:
    """Reject malformed guided keys and normalise lore documents to full shape."""
    if world_data is None:
        return None
    _validate_always_remember(world_data.get(KEY_ALWAYS_REMEMBER))
    normalised = dict(world_data)
    for key in LORE_DOCUMENT_KEYS:
        if normalised.get(key) is not None:
            normalised[key] = LoreDocument.model_validate(normalised[key]).model_dump()
    return normalised
