"""Plain-SQL prerequisite rows for repository tests.

Only inserts memory_template / memory_playthrough / memory_source / memory_span rows.
Never imports another agent's repository module.
"""

from uuid import UUID, uuid4

from app.models.common import ScopeKind
from psycopg import AsyncConnection

DEFAULT_CONTENT_HASH = "test-content-hash"

INSERT_TEMPLATE_SQL = """
INSERT INTO memory_template (
    template_id, scenario_id, publish_revision, mode, direct_status,
    enrichment_status, content_hash
) VALUES (
    %(template_id)s, %(scenario_id)s, %(publish_revision)s, %(mode)s,
    %(direct_status)s, %(enrichment_status)s, %(content_hash)s
)
"""

INSERT_PLAYTHROUGH_SQL = """
INSERT INTO memory_playthrough (playthrough_id, template_id)
VALUES (%(playthrough_id)s, %(template_id)s)
"""

INSERT_SOURCE_SQL = """
INSERT INTO memory_source (
    source_id, scope_kind, scope_id, source_kind, source_ref, sequence, content, content_hash
) VALUES (
    %(source_id)s, %(scope_kind)s, %(scope_id)s, 'turn_narration', %(source_ref)s,
    %(sequence)s, 'test source content', %(content_hash)s
)
"""

INSERT_SPAN_SQL = """
INSERT INTO memory_span (
    span_id, source_id, scope_kind, scope_id, sequence, ordinal,
    start_offset, end_offset, text, token_count, label
) VALUES (
    %(span_id)s, %(source_id)s, %(scope_kind)s, %(scope_id)s, %(sequence)s,
    %(ordinal)s, 0, 10, 'test span text', 2, %(label)s
)
"""


async def insert_template(
    connection: AsyncConnection,
    *,
    scenario_id: UUID | None = None,
    publish_revision: int = 0,
    mode: str = "master",
) -> UUID:
    template_id = uuid4()
    await connection.execute(
        INSERT_TEMPLATE_SQL,
        {
            "template_id": template_id,
            "scenario_id": scenario_id or uuid4(),
            "publish_revision": publish_revision,
            "mode": mode,
            "direct_status": "ready",
            "enrichment_status": "not_needed",
            "content_hash": DEFAULT_CONTENT_HASH,
        },
    )
    return template_id


async def insert_playthrough(
    connection: AsyncConnection, *, template_id: UUID | None = None
) -> UUID:
    playthrough_id = uuid4()
    await connection.execute(
        INSERT_PLAYTHROUGH_SQL,
        {"playthrough_id": playthrough_id, "template_id": template_id},
    )
    return playthrough_id


async def insert_source(
    connection: AsyncConnection,
    *,
    scope_kind: ScopeKind,
    scope_id: UUID,
    sequence: int = 1,
) -> UUID:
    source_id = uuid4()
    await connection.execute(
        INSERT_SOURCE_SQL,
        {
            "source_id": source_id,
            "scope_kind": scope_kind,
            "scope_id": scope_id,
            "source_ref": str(source_id),
            "sequence": sequence,
            "content_hash": str(uuid4()),
        },
    )
    return source_id


async def insert_span(
    connection: AsyncConnection,
    *,
    source_id: UUID,
    scope_kind: ScopeKind,
    scope_id: UUID,
    sequence: int = 1,
    ordinal: int = 1,
) -> UUID:
    span_id = uuid4()
    await connection.execute(
        INSERT_SPAN_SQL,
        {
            "span_id": span_id,
            "source_id": source_id,
            "scope_kind": scope_kind,
            "scope_id": scope_id,
            "sequence": sequence,
            "ordinal": ordinal,
            "label": f"S{sequence}.{ordinal}",
        },
    )
    return span_id
