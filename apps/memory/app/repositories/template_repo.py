"""Repository for memory_template. SQL lives only here."""

from uuid import UUID

from app.models.common import TemplateDirectStatus, TemplateEnrichmentStatus
from app.models.purge import TemplateGcCandidate, TemplateScope
from app.models.templates import TemplateCreate, TemplateRow
from psycopg import AsyncConnection
from psycopg.rows import class_row

INSERT_TEMPLATE_SQL = """
INSERT INTO memory_template
    (scenario_id, publish_revision, mode, direct_status, enrichment_status, content_hash)
VALUES
    (%(scenario_id)s, %(publish_revision)s, %(mode)s, %(direct_status)s,
     %(enrichment_status)s, %(content_hash)s)
ON CONFLICT (scenario_id, publish_revision) DO NOTHING
RETURNING *
"""

SELECT_TEMPLATE_BY_REVISION_SQL = """
SELECT * FROM memory_template
WHERE scenario_id = %(scenario_id)s AND publish_revision = %(publish_revision)s
"""

SELECT_TEMPLATE_BY_ID_SQL = (
    "SELECT * FROM memory_template WHERE template_id = %(template_id)s"
)

UPDATE_TEMPLATE_STATUSES_SQL = """
UPDATE memory_template
SET direct_status = COALESCE(%(direct_status)s, direct_status),
    enrichment_status = COALESCE(%(enrichment_status)s, enrichment_status)
WHERE template_id = %(template_id)s
RETURNING *
"""

LIST_TEMPLATES_BY_ENRICHMENT_SQL = """
SELECT * FROM memory_template
WHERE enrichment_status = ANY(%(statuses)s) AND direct_status = 'ready'
ORDER BY created_at, template_id
"""

SET_ENRICHMENT_SQL = """
UPDATE memory_template
SET enrichment_status = %(status)s, enrichment_error = %(error)s
WHERE template_id = %(template_id)s
RETURNING *
"""


async def create_template_with_status(
    connection: AsyncConnection, template: TemplateCreate
) -> tuple[TemplateRow, bool]:
    """Idempotent on (scenario_id, publish_revision); the bool is True only when this
    call inserted the row. A concurrent insert of the same key waits for that
    transaction to finish, then reads its committed row."""
    async with connection.cursor(row_factory=class_row(TemplateRow)) as cursor:
        await cursor.execute(INSERT_TEMPLATE_SQL, template.model_dump())
        inserted = await cursor.fetchone()
        if inserted is not None:
            return inserted, True
        await cursor.execute(
            SELECT_TEMPLATE_BY_REVISION_SQL,
            {
                "scenario_id": template.scenario_id,
                "publish_revision": template.publish_revision,
            },
        )
        existing = await cursor.fetchone()
    assert existing is not None
    return existing, False


async def create_template(
    connection: AsyncConnection, template: TemplateCreate
) -> TemplateRow:
    """Idempotent on (scenario_id, publish_revision)."""
    row, _is_inserted = await create_template_with_status(connection, template)
    return row


async def get_template(
    connection: AsyncConnection, template_id: UUID
) -> TemplateRow | None:
    async with connection.cursor(row_factory=class_row(TemplateRow)) as cursor:
        await cursor.execute(SELECT_TEMPLATE_BY_ID_SQL, {"template_id": template_id})
        return await cursor.fetchone()


async def get_template_by_revision(
    connection: AsyncConnection, scenario_id: UUID, publish_revision: int
) -> TemplateRow | None:
    async with connection.cursor(row_factory=class_row(TemplateRow)) as cursor:
        await cursor.execute(
            SELECT_TEMPLATE_BY_REVISION_SQL,
            {"scenario_id": scenario_id, "publish_revision": publish_revision},
        )
        return await cursor.fetchone()


async def update_template_statuses(
    connection: AsyncConnection,
    template_id: UUID,
    direct_status: TemplateDirectStatus | None,
    enrichment_status: TemplateEnrichmentStatus | None,
) -> TemplateRow | None:
    async with connection.cursor(row_factory=class_row(TemplateRow)) as cursor:
        await cursor.execute(
            UPDATE_TEMPLATE_STATUSES_SQL,
            {
                "template_id": template_id,
                "direct_status": direct_status,
                "enrichment_status": enrichment_status,
            },
        )
        return await cursor.fetchone()


async def list_templates_by_enrichment_status(
    connection: AsyncConnection, statuses: list[TemplateEnrichmentStatus]
) -> list[TemplateRow]:
    async with connection.cursor(row_factory=class_row(TemplateRow)) as cursor:
        await cursor.execute(LIST_TEMPLATES_BY_ENRICHMENT_SQL, {"statuses": statuses})
        return await cursor.fetchall()


async def set_enrichment_status(
    connection: AsyncConnection,
    template_id: UUID,
    status: TemplateEnrichmentStatus,
    error: str | None,
) -> TemplateRow | None:
    async with connection.cursor(row_factory=class_row(TemplateRow)) as cursor:
        await cursor.execute(
            SET_ENRICHMENT_SQL,
            {"template_id": template_id, "status": status, "error": error},
        )
        return await cursor.fetchone()


LOCK_TEMPLATE_FOR_UPDATE_SQL = (
    "SELECT template_id FROM memory_template "
    "WHERE template_id = %(template_id)s FOR UPDATE"
)
LOCK_TEMPLATE_FOR_SHARE_SQL = (
    "SELECT template_id FROM memory_template "
    "WHERE template_id = %(template_id)s FOR SHARE"
)
DELETE_TEMPLATE_SQL = "DELETE FROM memory_template WHERE template_id = %(template_id)s"
LIST_TEMPLATE_IDS_FOR_SCENARIOS_SQL = """
SELECT template_id FROM memory_template
WHERE scenario_id = ANY(%(scenario_ids)s::uuid[])
ORDER BY scenario_id, publish_revision
"""
LIST_TEMPLATE_SCOPES_SQL = """
SELECT template_id, scenario_id, publish_revision, created_at
FROM memory_template
ORDER BY created_at, template_id
"""
LIST_GC_CANDIDATES_SQL = """
WITH latest_ready AS (
    SELECT DISTINCT ON (scenario_id) template_id
    FROM memory_template
    WHERE direct_status = 'ready'
    ORDER BY scenario_id, publish_revision DESC
)
SELECT template.template_id,
    EXISTS (
        SELECT 1 FROM memory_playthrough AS playthrough
        WHERE playthrough.template_id = template.template_id
    ) AS is_referenced
FROM memory_template AS template
WHERE template.template_id NOT IN (SELECT template_id FROM latest_ready)
    AND (
        template.direct_status = 'ready'
        OR template.created_at < now() - make_interval(secs => %(failed_age_seconds)s)
    )
ORDER BY template.created_at, template.template_id
"""


async def lock_template_for_update(
    connection: AsyncConnection, template_id: UUID
) -> bool:
    """Waits for any transaction holding the share lock (an in-flight extraction apply)."""
    async with connection.cursor() as cursor:
        await cursor.execute(LOCK_TEMPLATE_FOR_UPDATE_SQL, {"template_id": template_id})
        return await cursor.fetchone() is not None


async def lock_template_for_share(
    connection: AsyncConnection, template_id: UUID
) -> bool:
    async with connection.cursor() as cursor:
        await cursor.execute(LOCK_TEMPLATE_FOR_SHARE_SQL, {"template_id": template_id})
        return await cursor.fetchone() is not None


async def delete_template(connection: AsyncConnection, template_id: UUID) -> bool:
    async with connection.cursor() as cursor:
        await cursor.execute(DELETE_TEMPLATE_SQL, {"template_id": template_id})
        return cursor.rowcount > 0


async def list_template_ids_for_scenarios(
    connection: AsyncConnection, scenario_ids: list[UUID]
) -> list[UUID]:
    if not scenario_ids:
        return []
    async with connection.cursor() as cursor:
        await cursor.execute(
            LIST_TEMPLATE_IDS_FOR_SCENARIOS_SQL, {"scenario_ids": scenario_ids}
        )
        return [row[0] for row in await cursor.fetchall()]


async def list_template_scopes(connection: AsyncConnection) -> list[TemplateScope]:
    async with connection.cursor(row_factory=class_row(TemplateScope)) as cursor:
        await cursor.execute(LIST_TEMPLATE_SCOPES_SQL)
        return await cursor.fetchall()


async def list_gc_candidates(
    connection: AsyncConnection, failed_age_seconds: int
) -> list[TemplateGcCandidate]:
    async with connection.cursor(row_factory=class_row(TemplateGcCandidate)) as cursor:
        await cursor.execute(
            LIST_GC_CANDIDATES_SQL, {"failed_age_seconds": failed_age_seconds}
        )
        return await cursor.fetchall()
