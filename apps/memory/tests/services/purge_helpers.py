"""Committed-world builders and row counters for purge and template GC tests."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.models.evidence import EventCreate
from app.models.facts import AliasCreate, SceneStateCreate
from app.models.jobs import ExtractionBatchCreate
from app.repositories import (
    embedding_failure_repo,
    entity_repo,
    event_repo,
    extraction_batch_repo,
    scene_repo,
)
from psycopg import AsyncConnection, sql
from tests.repositories import helpers_retrieval as helpers
from tests.repositories.helpers_evidence import make_playthrough, make_template

CANARY = "CANARY-PURGE-TEXT-9f3a"
MODEL = helpers.DEFAULT_MODEL
EMBEDDING_VECTOR = [0.1, 0.2, 0.3]
FAILURE_CODE = "embedding_permanent_error"
UNRELATED_FAILURES_PER_BUILD = 2
FAILURE_TABLE = "memory_embedding_failure"
MODEL_TABLE = "memory_embedding_model"

SELECT_MEMORY_TABLES_SQL = (
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
    "AND table_name LIKE 'memory\\_%' ORDER BY table_name"
)
AGE_TEMPLATE_SQL = (
    "UPDATE memory_template SET direct_status = %(status)s, "
    "created_at = now() - make_interval(secs => %(age_seconds)s) "
    "WHERE template_id = %(template_id)s"
)
COUNT_ROWS_SQL = "SELECT count(*) FROM {table}"
COUNT_TEMPLATE_SQL = "SELECT count(*) FROM memory_template WHERE template_id = %s"


@dataclass(frozen=True)
class TemplateIds:
    template_id: UUID
    scenario_id: UUID
    entity_id: UUID
    fact_id: UUID
    span_id: UUID


@dataclass(frozen=True)
class PlaythroughIds:
    playthrough_id: UUID
    entity_id: UUID
    fact_id: UUID
    span_id: UUID


async def _embed_and_fail(
    connection: AsyncConnection, scope: helpers.Scope, span_id: UUID, fact_id: UUID
) -> None:
    await helpers.add_embedding(connection, "span", span_id, scope, EMBEDDING_VECTOR)
    await helpers.add_embedding(connection, "fact", fact_id, scope, EMBEDDING_VECTOR)
    for kind, target in (("span", uuid4()), ("fact", uuid4())):
        await embedding_failure_repo.record_failures(
            connection, kind, [target], MODEL[0], MODEL[1], FAILURE_CODE
        )
    await embedding_failure_repo.record_failures(
        connection, "span", [span_id], MODEL[0], MODEL[1], FAILURE_CODE
    )
    await embedding_failure_repo.record_failures(
        connection, "fact", [fact_id], MODEL[0], MODEL[1], FAILURE_CODE
    )


async def _add_batch(connection: AsyncConnection, scope: helpers.Scope) -> UUID:
    batch = await extraction_batch_repo.create_batch(
        connection,
        ExtractionBatchCreate(
            scope_kind=scope[0],
            scope_id=scope[1],
            from_seq=1,
            to_seq=2,
            status="applied",
            model="m",
            prompt_version=str(uuid4()),
            input_hash="h",
        ),
    )
    return batch.batch_id


async def build_template(
    connection: AsyncConnection,
    *,
    scenario_id: UUID | None = None,
    publish_revision: int = 1,
    direct_status: str = "ready",
    age_seconds: int = 0,
) -> TemplateIds:
    row = await make_template(
        connection, scenario_id=scenario_id, publish_revision=publish_revision
    )
    await connection.execute(
        AGE_TEMPLATE_SQL,
        {
            "status": direct_status,
            "age_seconds": age_seconds,
            "template_id": row.template_id,
        },
    )
    scope: helpers.Scope = ("template", row.template_id)
    entity_id = await helpers.add_entity(connection, scope, f"Keep {CANARY}")
    span = await helpers.add_span(connection, scope, text=f"lore {CANARY}", sequence=0)
    fact = await helpers.add_fact(
        connection, scope, entity_id, "knows", object_literal=CANARY
    )
    await helpers.link_fact_source(connection, fact.fact_id, span.span_id)
    await helpers.register_model(connection)
    await _embed_and_fail(connection, scope, span.span_id, fact.fact_id)
    await _add_batch(connection, scope)
    return TemplateIds(
        row.template_id, row.scenario_id, entity_id, fact.fact_id, span.span_id
    )


async def _add_playthrough_graph(
    connection: AsyncConnection,
    playthrough_id: UUID,
    template: TemplateIds | None,
    own_entity_id: UUID,
) -> None:
    scope: helpers.Scope = ("playthrough", playthrough_id)
    batch_id = await _add_batch(connection, scope)
    await event_repo.create_events(
        connection,
        [
            EventCreate(
                playthrough_id=playthrough_id,
                sequence=1,
                turn_id=uuid4(),
                event_kind="roll",
                event_key="k",
                is_accepted=True,
                payload={},
            )
        ],
    )
    await scene_repo.append_scene_state(
        connection,
        SceneStateCreate(
            playthrough_id=playthrough_id,
            valid_from_seq=1,
            location_entity_id=own_entity_id,
            present_entity_ids=[own_entity_id],
            extraction_batch_id=batch_id,
        ),
    )
    commitment = await helpers.add_commitment(
        connection, playthrough_id, own_entity_id, opened_seq=1
    )
    await helpers.add_commitment_status(connection, commitment.commitment_id, 2, "open")
    if template is not None:
        await helpers.supersede_fact(
            connection, playthrough_id, template.fact_id, at_seq=3
        )


async def build_playthrough(
    connection: AsyncConnection, template: TemplateIds | None = None
) -> PlaythroughIds:
    row = await make_playthrough(
        connection, template_id=template.template_id if template else None
    )
    playthrough_id = row.playthrough_id
    scope: helpers.Scope = ("playthrough", playthrough_id)
    own_entity_id = await helpers.add_entity(connection, scope, f"Hero {CANARY}")
    span = await helpers.add_span(connection, scope, text=f"turn {CANARY}")
    fact = await helpers.add_fact(
        connection, scope, own_entity_id, "said", object_literal=CANARY
    )
    await helpers.link_fact_source(connection, fact.fact_id, span.span_id)
    await _add_aliases(connection, scope, own_entity_id, template)
    await helpers.register_model(connection)
    await _embed_and_fail(connection, scope, span.span_id, fact.fact_id)
    await _add_playthrough_graph(connection, playthrough_id, template, own_entity_id)
    return PlaythroughIds(playthrough_id, own_entity_id, fact.fact_id, span.span_id)


async def _add_aliases(
    connection: AsyncConnection,
    scope: helpers.Scope,
    own_entity_id: UUID,
    template: TemplateIds | None,
) -> None:
    targets = [own_entity_id]
    if template is not None:
        targets.append(template.entity_id)
        await helpers.add_fact(
            connection, scope, template.entity_id, "met", object_entity_id=own_entity_id
        )
        await helpers.add_fact(
            connection,
            scope,
            own_entity_id,
            "fears",
            object_entity_id=template.entity_id,
        )
    await entity_repo.add_aliases(
        connection,
        [
            AliasCreate(
                entity_id=target,
                scope_kind=scope[0],
                scope_id=scope[1],
                alias="Alias",
                alias_normalized="alias",
            )
            for target in targets
        ],
    )


async def table_counts(connection: AsyncConnection) -> dict[str, int]:
    cursor = await connection.execute(SELECT_MEMORY_TABLES_SQL)
    names = [row[0] for row in await cursor.fetchall()]
    counts: dict[str, int] = {}
    for name in names:
        statement = sql.SQL(COUNT_ROWS_SQL).format(table=sql.Identifier(name))
        result = await (await connection.execute(statement)).fetchone()
        assert result is not None
        counts[name] = int(result[0])
    return counts


async def template_exists(connection: AsyncConnection, template_id: UUID) -> bool:
    result = await (
        await connection.execute(COUNT_TEMPLATE_SQL, (template_id,))
    ).fetchone()
    assert result is not None
    return int(result[0]) == 1
