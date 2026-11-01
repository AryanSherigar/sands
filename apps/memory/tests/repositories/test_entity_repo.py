"""Repository tests for app.repositories.entity_repo against a real Postgres DB."""

from uuid import UUID, uuid4

import pytest
from app.models.common import ScopeKind
from app.models.facts import AliasCreate, EntityCreate, EntityRow
from app.repositories import entity_repo
from psycopg import AsyncConnection


async def _create_entity(
    connection: AsyncConnection,
    *,
    scope_kind: ScopeKind,
    scope_id: UUID,
    authored_entity_id: UUID | None = None,
    canonical_name: str = "Elowen",
    entity_type: str = "npc",
) -> EntityRow:
    return await entity_repo.create_entity(
        connection,
        EntityCreate(
            scope_kind=scope_kind,
            scope_id=scope_id,
            authored_entity_id=authored_entity_id,
            entity_type=entity_type,
            canonical_name=canonical_name,
            provenance="authored" if authored_entity_id else "extracted",
            first_seen_seq=1,
        ),
    )


async def test_create_entity_idempotent_on_authored_id(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    authored_entity_id = uuid4()

    first = await _create_entity(
        db_connection,
        scope_kind="template",
        scope_id=scope_id,
        authored_entity_id=authored_entity_id,
    )
    second = await _create_entity(
        db_connection,
        scope_kind="template",
        scope_id=scope_id,
        authored_entity_id=authored_entity_id,
        canonical_name="A Different Name",
    )

    assert first.entity_id == second.entity_id
    assert second.canonical_name == first.canonical_name

    all_rows = await entity_repo.get_entities(
        db_connection, scopes=[("template", scope_id)]
    )
    assert len(all_rows) == 1


async def test_create_entity_extracted_entities_are_plain_inserts(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()

    first = await _create_entity(
        db_connection, scope_kind="playthrough", scope_id=scope_id
    )
    second = await _create_entity(
        db_connection, scope_kind="playthrough", scope_id=scope_id
    )

    assert first.entity_id != second.entity_id

    all_rows = await entity_repo.get_entities(
        db_connection, scopes=[("playthrough", scope_id)]
    )
    assert len(all_rows) == 2


async def test_get_entities_scope_isolation(db_connection: AsyncConnection) -> None:
    scope_a = uuid4()
    scope_b = uuid4()

    entity_a = await _create_entity(
        db_connection,
        scope_kind="playthrough",
        scope_id=scope_a,
        canonical_name="Rowan",
    )
    entity_b = await _create_entity(
        db_connection,
        scope_kind="playthrough",
        scope_id=scope_b,
        canonical_name="Rowan",
    )

    rows_a = await entity_repo.get_entities(
        db_connection, scopes=[("playthrough", scope_a)]
    )
    rows_b = await entity_repo.get_entities(
        db_connection, scopes=[("playthrough", scope_b)]
    )

    assert {row.entity_id for row in rows_a} == {entity_a.entity_id}
    assert {row.entity_id for row in rows_b} == {entity_b.entity_id}


async def test_get_entities_filters_by_entity_ids(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    entity_one = await _create_entity(
        db_connection, scope_kind="template", scope_id=scope_id
    )
    await _create_entity(db_connection, scope_kind="template", scope_id=scope_id)

    rows = await entity_repo.get_entities(
        db_connection,
        scopes=[("template", scope_id)],
        entity_ids=[entity_one.entity_id],
    )

    assert {row.entity_id for row in rows} == {entity_one.entity_id}


async def test_get_entities_returns_empty_for_no_scopes(
    db_connection: AsyncConnection,
) -> None:
    assert await entity_repo.get_entities(db_connection, scopes=[]) == []


async def test_add_aliases_idempotent(db_connection: AsyncConnection) -> None:
    scope_id = uuid4()
    entity = await _create_entity(
        db_connection, scope_kind="playthrough", scope_id=scope_id
    )
    alias = AliasCreate(
        entity_id=entity.entity_id,
        scope_kind="playthrough",
        scope_id=scope_id,
        alias="The Wanderer",
        alias_normalized=entity_repo.normalize_alias("The Wanderer"),
    )

    first = await entity_repo.add_aliases(db_connection, [alias])
    second = await entity_repo.add_aliases(db_connection, [alias])

    assert first == second

    matches = await entity_repo.find_entities_by_alias(
        db_connection,
        scopes=[("playthrough", scope_id)],
        alias_normalized_values=[alias.alias_normalized],
    )
    assert len(matches) == 1


async def _create_template_kestrels(
    connection: AsyncConnection, template_1: UUID, template_2: UUID
) -> dict:
    return {
        ("template", template_1): await _create_entity(
            connection,
            scope_kind="template",
            scope_id=template_1,
            canonical_name="Kestrel",
        ),
        ("template", template_2): await _create_entity(
            connection,
            scope_kind="template",
            scope_id=template_2,
            canonical_name="Kestrel",
        ),
    }


async def _create_playthrough_kestrels(
    connection: AsyncConnection, playthrough_1: UUID, playthrough_2: UUID
) -> dict:
    return {
        ("playthrough", playthrough_1): await _create_entity(
            connection,
            scope_kind="playthrough",
            scope_id=playthrough_1,
            canonical_name="Kestrel",
        ),
        ("playthrough", playthrough_2): await _create_entity(
            connection,
            scope_kind="playthrough",
            scope_id=playthrough_2,
            canonical_name="Kestrel",
        ),
    }


async def _create_kestrel_entities(
    connection: AsyncConnection,
) -> tuple[dict, UUID, UUID, UUID, UUID]:
    template_1, template_2 = uuid4(), uuid4()
    playthrough_1, playthrough_2 = uuid4(), uuid4()
    template_entities = await _create_template_kestrels(
        connection, template_1, template_2
    )
    playthrough_entities = await _create_playthrough_kestrels(
        connection, playthrough_1, playthrough_2
    )
    scoped_entities = {**template_entities, **playthrough_entities}
    return scoped_entities, template_1, template_2, playthrough_1, playthrough_2


async def _add_kestrel_aliases(
    connection: AsyncConnection, scoped_entities: dict, alias_normalized: str
) -> None:
    for (scope_kind, scope_id), entity in scoped_entities.items():
        await entity_repo.add_aliases(
            connection,
            [
                AliasCreate(
                    entity_id=entity.entity_id,
                    scope_kind=scope_kind,
                    scope_id=scope_id,
                    alias="Kestrel",
                    alias_normalized=alias_normalized,
                )
            ],
        )


async def _setup_kestrel_entities(
    connection: AsyncConnection,
) -> tuple[dict, tuple, str]:
    (
        scoped_entities,
        template_1,
        _template_2,
        playthrough_1,
        _playthrough_2,
    ) = await _create_kestrel_entities(connection)
    alias_normalized = entity_repo.normalize_alias("Kestrel")
    await _add_kestrel_aliases(connection, scoped_entities, alias_normalized)
    return scoped_entities, (template_1, playthrough_1), alias_normalized


async def test_find_entities_by_alias_scope_isolation(
    db_connection: AsyncConnection,
) -> None:
    (
        scoped_entities,
        (template_1, playthrough_1),
        alias_normalized,
    ) = await _setup_kestrel_entities(db_connection)

    matches = await entity_repo.find_entities_by_alias(
        db_connection,
        scopes=[("template", template_1), ("playthrough", playthrough_1)],
        alias_normalized_values=[alias_normalized],
    )

    matched_ids = {row.entity_id for _, row in matches}
    assert matched_ids == {
        scoped_entities[("template", template_1)].entity_id,
        scoped_entities[("playthrough", playthrough_1)].entity_id,
    }
    assert all(alias_value == alias_normalized for alias_value, _ in matches)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("The Wanderer", "the wanderer"),
        ("  Spaced   Out  ", "spaced out"),
        ("'Quoted Name.'", "quoted name"),
        ("ALLCAPS", "allcaps"),
    ],
)
def test_normalize_alias(raw: str, expected: str) -> None:
    assert entity_repo.normalize_alias(raw) == expected


def _player_alias(
    *, entity_id: UUID, scope_id: UUID, alias_normalized: str
) -> AliasCreate:
    return AliasCreate(
        entity_id=entity_id,
        scope_kind="playthrough",
        scope_id=scope_id,
        alias="Rook",
        alias_normalized=alias_normalized,
    )


async def test_add_aliases_same_entity_and_alias_two_playthrough_scopes_two_rows(
    db_connection: AsyncConnection,
) -> None:
    template_id = uuid4()
    entity = await _create_entity(
        db_connection,
        scope_kind="template",
        scope_id=template_id,
        authored_entity_id=uuid4(),
    )
    alias_normalized = entity_repo.normalize_alias("Rook")
    playthrough_1, playthrough_2 = uuid4(), uuid4()

    rows = await entity_repo.add_aliases(
        db_connection,
        [
            _player_alias(
                entity_id=entity.entity_id,
                scope_id=playthrough_1,
                alias_normalized=alias_normalized,
            ),
            _player_alias(
                entity_id=entity.entity_id,
                scope_id=playthrough_2,
                alias_normalized=alias_normalized,
            ),
        ],
    )

    assert len(rows) == 2
    assert {row.scope_id for row in rows} == {playthrough_1, playthrough_2}
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_alias WHERE entity_id = %s", (entity.entity_id,)
    )
    assert await cursor.fetchone() == (2,)


async def test_add_aliases_same_scope_twice_one_row(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    entity = await _create_entity(
        db_connection, scope_kind="playthrough", scope_id=scope_id
    )
    alias_normalized = entity_repo.normalize_alias("Rook")
    alias = _player_alias(
        entity_id=entity.entity_id, scope_id=scope_id, alias_normalized=alias_normalized
    )

    await entity_repo.add_aliases(db_connection, [alias])
    await entity_repo.add_aliases(db_connection, [alias])

    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_alias WHERE entity_id = %s", (entity.entity_id,)
    )
    assert await cursor.fetchone() == (1,)


async def test_list_aliases_in_scopes_filters_by_scope(
    db_connection: AsyncConnection,
) -> None:
    playthrough_1, playthrough_2 = uuid4(), uuid4()
    entity_1 = await _create_entity(
        db_connection, scope_kind="playthrough", scope_id=playthrough_1
    )
    entity_2 = await _create_entity(
        db_connection, scope_kind="playthrough", scope_id=playthrough_2
    )
    alias_normalized = entity_repo.normalize_alias("Rook")
    await entity_repo.add_aliases(
        db_connection,
        [
            _player_alias(
                entity_id=entity_1.entity_id,
                scope_id=playthrough_1,
                alias_normalized=alias_normalized,
            ),
            _player_alias(
                entity_id=entity_2.entity_id,
                scope_id=playthrough_2,
                alias_normalized=alias_normalized,
            ),
        ],
    )

    rows = await entity_repo.list_aliases_in_scopes(
        db_connection, scopes=[("playthrough", playthrough_1)]
    )

    assert rows == [(alias_normalized, entity_1.entity_id)]


async def test_list_aliases_in_scopes_returns_empty_for_no_scopes(
    db_connection: AsyncConnection,
) -> None:
    assert await entity_repo.list_aliases_in_scopes(db_connection, scopes=[]) == []


async def test_get_entities_by_authored_ids_filters_by_scope_and_ids(
    db_connection: AsyncConnection,
) -> None:
    template_1, template_2 = uuid4(), uuid4()
    authored_id_1, authored_id_2 = uuid4(), uuid4()
    entity_1 = await _create_entity(
        db_connection,
        scope_kind="template",
        scope_id=template_1,
        authored_entity_id=authored_id_1,
    )
    await _create_entity(
        db_connection,
        scope_kind="template",
        scope_id=template_1,
        authored_entity_id=authored_id_2,
    )
    await _create_entity(
        db_connection,
        scope_kind="template",
        scope_id=template_2,
        authored_entity_id=authored_id_1,
    )

    rows = await entity_repo.get_entities_by_authored_ids(
        db_connection,
        scopes=[("template", template_1)],
        authored_entity_ids=[authored_id_1],
    )

    assert {row.entity_id for row in rows} == {entity_1.entity_id}


async def test_get_entities_by_authored_ids_returns_empty_for_no_scopes(
    db_connection: AsyncConnection,
) -> None:
    rows = await entity_repo.get_entities_by_authored_ids(
        db_connection, scopes=[], authored_entity_ids=[uuid4()]
    )
    assert rows == []
