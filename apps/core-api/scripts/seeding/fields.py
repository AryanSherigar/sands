"""Builders for state_schema field definitions shared by the generators."""

FieldDef = dict[str, object]
Schema = dict[str, FieldDef]


def number(low: int, high: int, initial: int) -> FieldDef:
    return {"type": "number", "min": low, "max": high, "initial": initial}


def flag(initial: bool = False) -> FieldDef:
    return {"type": "boolean", "initial": initial}


def enum(options: tuple[str, ...], initial: str) -> FieldDef:
    return {"type": "enum", "options": list(options), "initial": initial}


def group(fields: Schema, is_hidden: bool = True) -> FieldDef:
    definition: FieldDef = {"type": "object", "fields": fields}
    if is_hidden:
        definition["hidden"] = True
    return definition


def flatten_schema(schema: Schema) -> dict[str, FieldDef]:
    """Every leaf field path ("flags.cage_open") mapped to its definition."""
    flat: dict[str, FieldDef] = {}
    for name, definition in schema.items():
        _collect(name, definition, flat)
    return flat


def _collect(path: str, definition: FieldDef, flat: dict[str, FieldDef]) -> None:
    nested = definition.get("fields")
    if definition.get("type") != "object" or not isinstance(nested, dict):
        flat[path] = definition
        return
    for name, child in nested.items():
        _collect(f"{path}.{name}", child, flat)
