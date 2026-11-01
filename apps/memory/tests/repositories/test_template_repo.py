"""memory_template: idempotent create, revision coexistence, status updates."""

from uuid import uuid4

from app.models.templates import TemplateCreate
from app.repositories.template_repo import (
    create_template,
    get_template,
    get_template_by_revision,
    update_template_statuses,
)
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import make_template

DEFAULT_MODE = "master"
DEFAULT_DIRECT_STATUS = "ready"
DEFAULT_ENRICHMENT_STATUS = "not_needed"


def _template_create(scenario_id, publish_revision: int) -> TemplateCreate:
    return TemplateCreate(
        scenario_id=scenario_id,
        publish_revision=publish_revision,
        mode=DEFAULT_MODE,
        direct_status=DEFAULT_DIRECT_STATUS,
        enrichment_status=DEFAULT_ENRICHMENT_STATUS,
        content_hash="hash",
    )


async def test_create_template_returns_row(db_connection: AsyncConnection) -> None:
    scenario_id = uuid4()

    row = await create_template(db_connection, _template_create(scenario_id, 1))

    assert row.scenario_id == scenario_id
    assert row.publish_revision == 1
    assert row.template_id is not None


async def test_create_template_idempotent_reinsert_returns_existing_no_duplicate(
    db_connection: AsyncConnection,
) -> None:
    scenario_id = uuid4()
    first = await create_template(db_connection, _template_create(scenario_id, 1))

    second = await create_template(db_connection, _template_create(scenario_id, 1))

    assert second.template_id == first.template_id
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_template WHERE scenario_id = %s", (scenario_id,)
    )
    assert await cursor.fetchone() == (1,)


async def test_create_template_different_revisions_coexist(
    db_connection: AsyncConnection,
) -> None:
    scenario_id = uuid4()
    first = await create_template(db_connection, _template_create(scenario_id, 1))

    second = await create_template(db_connection, _template_create(scenario_id, 2))

    assert first.template_id != second.template_id
    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_template WHERE scenario_id = %s", (scenario_id,)
    )
    assert await cursor.fetchone() == (2,)


async def test_get_template_returns_row_by_id(db_connection: AsyncConnection) -> None:
    created = await make_template(db_connection)

    found = await get_template(db_connection, created.template_id)

    assert found == created


async def test_get_template_returns_none_when_missing(
    db_connection: AsyncConnection,
) -> None:
    assert await get_template(db_connection, uuid4()) is None


async def test_get_template_by_revision_returns_row(
    db_connection: AsyncConnection,
) -> None:
    scenario_id = uuid4()
    created = await make_template(
        db_connection, scenario_id=scenario_id, publish_revision=3
    )

    found = await get_template_by_revision(db_connection, scenario_id, 3)

    assert found == created


async def test_get_template_by_revision_returns_none_when_missing(
    db_connection: AsyncConnection,
) -> None:
    assert await get_template_by_revision(db_connection, uuid4(), 1) is None


async def test_update_template_statuses_updates_only_given_fields(
    db_connection: AsyncConnection,
) -> None:
    created = await make_template(db_connection)

    updated = await update_template_statuses(
        db_connection,
        created.template_id,
        direct_status="failed",
        enrichment_status=None,
    )

    assert updated is not None
    assert updated.direct_status == "failed"
    assert updated.enrichment_status == created.enrichment_status


async def test_update_template_statuses_missing_template_returns_none(
    db_connection: AsyncConnection,
) -> None:
    result = await update_template_statuses(
        db_connection, uuid4(), direct_status="failed", enrichment_status=None
    )

    assert result is None
