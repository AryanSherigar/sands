"""Lookups into a scenario's state_schema by dotted path."""


def field_at_path(
    state_schema: dict[str, object], path: str
) -> dict[str, object] | None:
    """The field definition at a dotted path, walking through object fields."""
    segments = path.split(".")
    current: object = state_schema.get(segments[0])
    for segment in segments[1:]:
        if not isinstance(current, dict) or current.get("type") != "object":
            return None
        nested = current.get("fields")
        current = nested.get(segment) if isinstance(nested, dict) else None
    return current if isinstance(current, dict) else None


def enum_option_values(raw_options: object) -> list[str]:
    """Option values of an enum field: plain strings or `{"value": ...}` dicts."""
    if not isinstance(raw_options, list):
        return []
    values: list[str] = []
    for option in raw_options:
        if isinstance(option, str):
            values.append(option)
        elif isinstance(option, dict) and "value" in option:
            values.append(str(option["value"]))
    return values
