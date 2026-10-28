"""Shared write rule for the legacy single mutation and its list."""

from collections.abc import Collection, Sequence

from app.models.condition import StateMutation


def mutation_columns(
    single_name: str,
    list_name: str,
    fields_set: Collection[str],
    single: StateMutation | None,
    listed: Sequence[StateMutation] | None,
) -> dict[str, object]:
    """Column values for a write: either shape is accepted, the single one is
    folded into the list, and the legacy column is cleared on that row."""
    if list_name in fields_set:
        return {list_name: _dump_all(listed or []), single_name: None}
    if single_name in fields_set:
        return {list_name: _dump_all([single] if single else []), single_name: None}
    return {}


def _dump_all(mutations: Sequence[StateMutation]) -> list[dict[str, object]]:
    return [mutation.model_dump(mode="json") for mutation in mutations]
