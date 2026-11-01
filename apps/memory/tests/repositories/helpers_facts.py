"""Prerequisite rows for fact_repo tests, inserted with plain SQL so these tests
do not depend on the repositories that own those tables."""

from uuid import UUID, uuid4

from app.models.common import Authority, ScopeKind
from app.models.facts import FactCreate, SupersessionCreate
from psycopg import AsyncConnection

TEMPLATE_SCOPE: ScopeKind = "template"
PLAYTHROUGH_SCOPE: ScopeKind = "playthrough"
AUTHORED_SEQUENCE = 0
DEFAULT_PUBLISH_REVISION = 1
DEFAULT_ENTITY_TYPE = "character"
DEFAULT_SOURCE_KIND = "turn_narration"
DEFAULT_SPAN_TEXT = "Mira swore an oath to the Red Guild."

INSERT_TEMPLATE = """
INSERT INTO memory_template
    (scenario_id, publish_revision, mode, direct_status, enrichment_status, content_hash)
VALUES (%s, %s, 'master', 'ready', 'not_needed', 'hash')
RETURNING template_id
"""

INSERT_PLAYTHROUGH = """
INSERT INTO memory_playthrough (template_id) VALUES (%s) RETURNING playthrough_id
"""

INSERT_ENTITY = """
INSERT INTO memory_entity
    (scope_kind, scope_id, entity_type, canonical_name, provenance, first_seen_seq)
VALUES (%s, %s, %s, %s, 'extracted', 0)
RETURNING entity_id
"""

INSERT_SOURCE = """
INSERT INTO memory_source
    (scope_kind, scope_id, source_kind, source_ref, sequence, content, content_hash)
VALUES (%s, %s, %s, %s, %s, %s, 'hash')
RETURNING source_id
"""

INSERT_SPAN = """
INSERT INTO memory_span
    (source_id, scope_kind, scope_id, sequence, ordinal, start_offset, end_offset,
     text, token_count, label)
VALUES (%s, %s, %s, %s, 0, 0, %s, %s, 1, 'S0.0')
RETURNING span_id
"""

DELETE_PLAYTHROUGH = "DELETE FROM memory_playthrough WHERE playthrough_id = %s"
COUNT_SUPERSESSIONS_FOR_FACT = (
    "SELECT count(*) FROM memory_supersession WHERE fact_id = %s"
)
COUNT_FACT_SOURCES_FOR_FACT = (
    "SELECT count(*) FROM memory_fact_source WHERE fact_id = %s"
)
COUNT_FACTS_BY_ID = "SELECT count(*) FROM memory_fact WHERE fact_id = %s"


async def _insert_returning_id(
    connection: AsyncConnection, statement: str, params: tuple[object, ...]
) -> UUID:
    cursor = await connection.execute(statement, params)
    row = await cursor.fetchone()
    assert row is not None
    return row[0]


async def insert_template(connection: AsyncConnection) -> UUID:
    return await _insert_returning_id(
        connection, INSERT_TEMPLATE, (uuid4(), DEFAULT_PUBLISH_REVISION)
    )


async def insert_playthrough(
    connection: AsyncConnection, template_id: UUID | None
) -> UUID:
    return await _insert_returning_id(connection, INSERT_PLAYTHROUGH, (template_id,))


async def insert_entity(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID, name: str
) -> UUID:
    params = (scope_kind, scope_id, DEFAULT_ENTITY_TYPE, name)
    return await _insert_returning_id(connection, INSERT_ENTITY, params)


async def insert_span(
    connection: AsyncConnection, scope_kind: ScopeKind, scope_id: UUID
) -> UUID:
    source_params = (
        scope_kind,
        scope_id,
        DEFAULT_SOURCE_KIND,
        str(uuid4()),
        AUTHORED_SEQUENCE,
        DEFAULT_SPAN_TEXT,
    )
    source_id = await _insert_returning_id(connection, INSERT_SOURCE, source_params)
    span_params = (
        source_id,
        scope_kind,
        scope_id,
        AUTHORED_SEQUENCE,
        len(DEFAULT_SPAN_TEXT),
        DEFAULT_SPAN_TEXT,
    )
    return await _insert_returning_id(connection, INSERT_SPAN, span_params)


async def count_rows(connection: AsyncConnection, statement: str, fact_id: UUID) -> int:
    cursor = await connection.execute(statement, (fact_id,))
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def delete_playthrough(connection: AsyncConnection, playthrough_id: UUID) -> None:
    await connection.execute(DELETE_PLAYTHROUGH, (playthrough_id,))


def make_fact(
    scope_kind: ScopeKind,
    scope_id: UUID,
    subject_entity_id: UUID,
    predicate: str,
    *,
    object_entity_id: UUID | None = None,
    object_literal: str | None = None,
    valid_from_seq: int = AUTHORED_SEQUENCE,
    authority: Authority = "extracted",
    authored_fact_id: UUID | None = None,
    supersedes_authored_fact_id: UUID | None = None,
) -> FactCreate:
    return FactCreate(
        scope_kind=scope_kind,
        scope_id=scope_id,
        subject_entity_id=subject_entity_id,
        predicate=predicate,
        object_entity_id=object_entity_id,
        object_literal=object_literal,
        authority=authority,
        assertion="occurred",
        valid_from_seq=valid_from_seq,
        authored_fact_id=authored_fact_id,
        supersedes_authored_fact_id=supersedes_authored_fact_id,
    )


def make_supersession(
    playthrough_id: UUID,
    fact_id: UUID,
    at_seq: int,
    superseding_fact_id: UUID | None = None,
) -> SupersessionCreate:
    return SupersessionCreate(
        playthrough_id=playthrough_id,
        fact_id=fact_id,
        at_seq=at_seq,
        superseding_fact_id=superseding_fact_id,
        authority="extracted",
    )
