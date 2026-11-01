"""span_repo.first_unembedded_sequence: the lowest span sequence still blocking indexed_seq."""

from uuid import UUID

import pytest
from app.models.common import ScopeKind
from app.models.jobs import EmbeddingCreate, EmbeddingModelCreate
from app.repositories import embedding_failure_repo, embedding_repo, span_repo
from psycopg import AsyncConnection
from tests.repositories import helpers_entities

MODEL = ("model-a", "v1")
OTHER_MODEL = ("model-b", "v1")
DIM = 3
FAILURE_LIMIT = 3


@pytest.fixture
async def models(db_connection: AsyncConnection) -> None:
    for model, version in (MODEL, OTHER_MODEL):
        await embedding_repo.register_embedding_model(
            db_connection,
            EmbeddingModelCreate(
                model=model, model_version=version, dim=DIM, is_active=False
            ),
        )


async def make_span(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    sequence: int,
) -> UUID:
    source_id = await helpers_entities.insert_source(
        connection, scope_kind=scope_kind, scope_id=scope_id, sequence=sequence
    )
    return await helpers_entities.insert_span(
        connection,
        source_id=source_id,
        scope_kind=scope_kind,
        scope_id=scope_id,
        sequence=sequence,
    )


async def embed_span(
    connection: AsyncConnection,
    span_id: UUID,
    playthrough_id: UUID,
    model: tuple[str, str] = MODEL,
) -> None:
    await embedding_repo.insert_embeddings(
        connection,
        [
            EmbeddingCreate(
                target_kind="span",
                target_id=span_id,
                scope_kind="playthrough",
                scope_id=playthrough_id,
                model=model[0],
                model_version=model[1],
                dim=DIM,
                embedding=[0.1] * DIM,
                content_hash="hash",
            )
        ],
    )


async def first_sequence(
    connection: AsyncConnection,
    playthrough_id: UUID,
    model: tuple[str, str] = MODEL,
) -> int | None:
    return await span_repo.first_unembedded_sequence(
        connection, playthrough_id, model[0], model[1], FAILURE_LIMIT
    )


async def test_first_unembedded_sequence_is_none_without_spans(
    db_connection: AsyncConnection, models: None
) -> None:
    playthrough_id = await helpers_entities.insert_playthrough(db_connection)

    assert await first_sequence(db_connection, playthrough_id) is None


async def test_first_unembedded_sequence_returns_lowest_unembedded(
    db_connection: AsyncConnection, models: None
) -> None:
    playthrough_id = await helpers_entities.insert_playthrough(db_connection)
    span_ids = {
        sequence: await make_span(
            db_connection, "playthrough", playthrough_id, sequence
        )
        for sequence in (1, 2, 3)
    }
    assert await first_sequence(db_connection, playthrough_id) == 1

    await embed_span(db_connection, span_ids[1], playthrough_id)
    assert await first_sequence(db_connection, playthrough_id) == 2
    assert await first_sequence(db_connection, playthrough_id, OTHER_MODEL) == 1

    await embed_span(db_connection, span_ids[2], playthrough_id)
    await embed_span(db_connection, span_ids[3], playthrough_id)
    assert await first_sequence(db_connection, playthrough_id) is None


async def test_first_unembedded_sequence_ignores_spans_at_failure_limit(
    db_connection: AsyncConnection, models: None
) -> None:
    playthrough_id = await helpers_entities.insert_playthrough(db_connection)
    poisoned = await make_span(db_connection, "playthrough", playthrough_id, 1)
    retryable = await make_span(db_connection, "playthrough", playthrough_id, 2)
    for _ in range(FAILURE_LIMIT):
        await embedding_failure_repo.record_failures(
            db_connection, "span", [poisoned], *MODEL, "bad_request"
        )
    await embedding_failure_repo.record_failures(
        db_connection, "span", [retryable], *MODEL, "bad_request"
    )

    assert await first_sequence(db_connection, playthrough_id) == 2
    assert await first_sequence(db_connection, playthrough_id, OTHER_MODEL) == 1


async def test_first_unembedded_sequence_only_looks_at_its_own_playthrough(
    db_connection: AsyncConnection, models: None
) -> None:
    template_id = await helpers_entities.insert_template(db_connection)
    mine = await helpers_entities.insert_playthrough(
        db_connection, template_id=template_id
    )
    other = await helpers_entities.insert_playthrough(
        db_connection, template_id=template_id
    )
    await make_span(db_connection, "template", template_id, 0)
    await make_span(db_connection, "playthrough", other, 1)
    await make_span(db_connection, "playthrough", mine, 4)

    assert await first_sequence(db_connection, mine) == 4
