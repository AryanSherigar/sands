"""Repository for memory_entity and memory_alias (child table)."""

import re
from uuid import UUID

from app.models.common import ScopeKind
from app.models.facts import AliasCreate, AliasRow, EntityCreate, EntityRow
from psycopg import AsyncConnection, AsyncCursor, sql
from psycopg.rows import class_row, dict_row

_WHITESPACE_PATTERN = re.compile(r"\s+")
_EDGE_PUNCTUATION_PATTERN = re.compile(r"^\W+|\W+$")

CREATE_ENTITY_SQL = """
INSERT INTO memory_entity (
    scope_kind, scope_id, authored_entity_id, entity_type,
    canonical_name, provenance, first_seen_seq, is_player
) VALUES (
    %(scope_kind)s, %(scope_id)s, %(authored_entity_id)s, %(entity_type)s,
    %(canonical_name)s, %(provenance)s, %(first_seen_seq)s, %(is_player)s
)
ON CONFLICT (scope_kind, scope_id, authored_entity_id) DO NOTHING
RETURNING *
"""

SELECT_ENTITY_BY_AUTHORED_ID_SQL = """
SELECT * FROM memory_entity
WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s
    AND authored_entity_id = %(authored_entity_id)s
"""

GET_ENTITIES_SQL = "SELECT * FROM memory_entity WHERE ({predicate})"

CREATE_ALIAS_SQL = """
INSERT INTO memory_alias (entity_id, scope_kind, scope_id, alias, alias_normalized)
VALUES (%(entity_id)s, %(scope_kind)s, %(scope_id)s, %(alias)s, %(alias_normalized)s)
ON CONFLICT (entity_id, scope_kind, scope_id, alias_normalized) DO NOTHING
RETURNING *
"""

SELECT_ALIAS_SQL = """
SELECT * FROM memory_alias
WHERE entity_id = %(entity_id)s AND scope_kind = %(scope_kind)s
    AND scope_id = %(scope_id)s AND alias_normalized = %(alias_normalized)s
"""

LIST_ALIASES_IN_SCOPES_SQL = (
    "SELECT alias_normalized, entity_id FROM memory_alias WHERE ({predicate})"
)

FIND_ENTITIES_BY_ALIAS_SQL = """
SELECT
    alias.alias_normalized AS matched_alias_normalized,
    entity.entity_id AS entity_id,
    entity.scope_kind AS scope_kind,
    entity.scope_id AS scope_id,
    entity.authored_entity_id AS authored_entity_id,
    entity.entity_type AS entity_type,
    entity.canonical_name AS canonical_name,
    entity.provenance AS provenance,
    entity.first_seen_seq AS first_seen_seq,
    entity.is_player AS is_player
FROM memory_alias AS alias
JOIN memory_entity AS entity ON entity.entity_id = alias.entity_id
WHERE ({predicate}) AND alias.alias_normalized = ANY(%s)
"""


def normalize_alias(alias: str) -> str:
    collapsed = _WHITESPACE_PATTERN.sub(" ", alias.casefold()).strip()
    return _EDGE_PUNCTUATION_PATTERN.sub("", collapsed)


def _scope_predicate(
    scopes: list[tuple[ScopeKind, UUID]], column_prefix: str = ""
) -> tuple[sql.Composed, list[object]]:
    prefix = f"{column_prefix}." if column_prefix else ""
    clause = sql.SQL(" OR ").join(
        sql.SQL(f"({prefix}scope_kind = %s AND {prefix}scope_id = %s)") for _ in scopes
    )
    params: list[object] = [value for pair in scopes for value in pair]
    return clause, params


async def create_entity(connection: AsyncConnection, entity: EntityCreate) -> EntityRow:
    async with connection.cursor(row_factory=class_row(EntityRow)) as cursor:
        await cursor.execute(CREATE_ENTITY_SQL, entity.model_dump())
        row = await cursor.fetchone()
        if row is not None:
            return row
        await cursor.execute(SELECT_ENTITY_BY_AUTHORED_ID_SQL, entity.model_dump())
        existing = await cursor.fetchone()
    if existing is None:
        raise RuntimeError("Entity insert conflicted but no existing row was found.")
    return existing


async def get_entities(
    connection: AsyncConnection,
    scopes: list[tuple[ScopeKind, UUID]],
    entity_ids: list[UUID] | None = None,
) -> list[EntityRow]:
    if not scopes:
        return []
    predicate, params = _scope_predicate(scopes)
    query = sql.SQL(GET_ENTITIES_SQL).format(predicate=predicate)
    if entity_ids is not None:
        query = query + sql.SQL(" AND entity_id = ANY(%s)")
        params = [*params, entity_ids]
    async with connection.cursor(row_factory=class_row(EntityRow)) as cursor:
        await cursor.execute(query, params)
        return await cursor.fetchall()


async def _insert_or_get_alias(
    cursor: AsyncCursor[AliasRow], alias: AliasCreate
) -> AliasRow:
    await cursor.execute(CREATE_ALIAS_SQL, alias.model_dump())
    row = await cursor.fetchone()
    if row is not None:
        return row
    await cursor.execute(
        SELECT_ALIAS_SQL,
        {
            "entity_id": alias.entity_id,
            "scope_kind": alias.scope_kind,
            "scope_id": alias.scope_id,
            "alias_normalized": alias.alias_normalized,
        },
    )
    existing = await cursor.fetchone()
    if existing is None:
        raise RuntimeError("Alias insert conflicted but no existing row was found.")
    return existing


async def add_aliases(
    connection: AsyncConnection, aliases: list[AliasCreate]
) -> list[AliasRow]:
    rows: list[AliasRow] = []
    async with connection.cursor(row_factory=class_row(AliasRow)) as cursor:
        for alias in aliases:
            rows.append(await _insert_or_get_alias(cursor, alias))
    return rows


def _split_alias_match(row: dict[str, object]) -> tuple[str, EntityRow]:
    matched = row.pop("matched_alias_normalized")
    return str(matched), EntityRow(**row)


async def find_entities_by_alias(
    connection: AsyncConnection,
    scopes: list[tuple[ScopeKind, UUID]],
    alias_normalized_values: list[str],
) -> list[tuple[str, EntityRow]]:
    if not scopes or not alias_normalized_values:
        return []
    predicate, params = _scope_predicate(scopes, column_prefix="alias")
    query = sql.SQL(FIND_ENTITIES_BY_ALIAS_SQL).format(predicate=predicate)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(query, [*params, alias_normalized_values])
        rows = await cursor.fetchall()
    return [_split_alias_match(row) for row in rows]


async def list_aliases_in_scopes(
    connection: AsyncConnection, scopes: list[tuple[ScopeKind, UUID]]
) -> list[tuple[str, UUID]]:
    if not scopes:
        return []
    predicate, params = _scope_predicate(scopes)
    query = sql.SQL(LIST_ALIASES_IN_SCOPES_SQL).format(predicate=predicate)
    async with connection.cursor() as cursor:
        await cursor.execute(query, params)
        rows = await cursor.fetchall()
    return [(row[0], row[1]) for row in rows]


async def get_entities_by_authored_ids(
    connection: AsyncConnection,
    scopes: list[tuple[ScopeKind, UUID]],
    authored_entity_ids: list[UUID],
) -> list[EntityRow]:
    if not scopes or not authored_entity_ids:
        return []
    predicate, params = _scope_predicate(scopes)
    query = sql.SQL(GET_ENTITIES_SQL).format(predicate=predicate)
    query = query + sql.SQL(" AND authored_entity_id = ANY(%s)")
    params = [*params, authored_entity_ids]
    async with connection.cursor(row_factory=class_row(EntityRow)) as cursor:
        await cursor.execute(query, params)
        return await cursor.fetchall()


DELETE_SCOPE_ENTITIES_SQL = (
    "DELETE FROM memory_entity "
    "WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s"
)


async def delete_scope_entities(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> int:
    async with connection.cursor() as cursor:
        await cursor.execute(
            DELETE_SCOPE_ENTITIES_SQL, {"scope_kind": scope_kind, "scope_id": scope_id}
        )
        return cursor.rowcount


DELETE_SCOPE_ALIASES_SQL = (
    "DELETE FROM memory_alias "
    "WHERE scope_kind = %(scope_kind)s AND scope_id = %(scope_id)s"
)


async def delete_scope_aliases(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> int:
    """Aliases are scoped separately from their entity: a playthrough can alias a
    template entity, and that row does not cascade when the playthrough's entities go."""
    async with connection.cursor() as cursor:
        await cursor.execute(
            DELETE_SCOPE_ALIASES_SQL, {"scope_kind": scope_kind, "scope_id": scope_id}
        )
        return cursor.rowcount
