"""Repository tests for app.repositories.embedding_repo against a real Postgres DB."""

from uuid import uuid4

import psycopg
import pytest
from app.models.jobs import EmbeddingCreate, EmbeddingModelCreate
from app.repositories import embedding_repo
from psycopg import AsyncConnection


async def test_register_embedding_model_idempotent(
    db_connection: AsyncConnection,
) -> None:
    model = EmbeddingModelCreate(
        model="text-embed", model_version="v1", dim=3, is_active=False
    )

    first = await embedding_repo.register_embedding_model(db_connection, model)
    second = await embedding_repo.register_embedding_model(db_connection, model)

    assert first == second


async def test_get_active_embedding_model_returns_none_when_none_active(
    db_connection: AsyncConnection,
) -> None:
    assert await embedding_repo.get_active_embedding_model(db_connection) is None


async def test_activate_embedding_model_switches_active_flag(
    db_connection: AsyncConnection,
) -> None:
    await embedding_repo.register_embedding_model(
        db_connection,
        EmbeddingModelCreate(model="a", model_version="v1", dim=3, is_active=True),
    )
    await embedding_repo.register_embedding_model(
        db_connection,
        EmbeddingModelCreate(model="b", model_version="v1", dim=3, is_active=False),
    )

    active = await embedding_repo.get_active_embedding_model(db_connection)
    assert active is not None
    assert active.model == "a"

    await embedding_repo.activate_embedding_model(db_connection, "b", "v1")

    active = await embedding_repo.get_active_embedding_model(db_connection)
    assert active is not None
    assert active.model == "b"


async def test_partial_unique_index_prevents_two_active_models(
    db_connection: AsyncConnection,
) -> None:
    await embedding_repo.register_embedding_model(
        db_connection,
        EmbeddingModelCreate(model="a", model_version="v1", dim=3, is_active=True),
    )
    await embedding_repo.register_embedding_model(
        db_connection,
        EmbeddingModelCreate(model="b", model_version="v1", dim=3, is_active=False),
    )

    with pytest.raises(psycopg.errors.UniqueViolation):
        async with db_connection.cursor() as cursor:
            await cursor.execute(
                "UPDATE memory_embedding_model SET is_active = true WHERE model = 'b'"
            )


async def test_create_embeddings_idempotent_and_vector_round_trips(
    db_connection: AsyncConnection,
) -> None:
    await embedding_repo.register_embedding_model(
        db_connection,
        EmbeddingModelCreate(model="a", model_version="v1", dim=3, is_active=True),
    )
    target_id = uuid4()
    scope_id = uuid4()
    embedding = EmbeddingCreate(
        target_kind="span",
        target_id=target_id,
        scope_kind="playthrough",
        scope_id=scope_id,
        model="a",
        model_version="v1",
        dim=3,
        embedding=[0.1, 0.2, 0.3],
        content_hash="hash",
    )

    first = await embedding_repo.create_embeddings(db_connection, [embedding])
    second = await embedding_repo.create_embeddings(db_connection, [embedding])

    assert len(first) == 1
    assert first[0].embedding == pytest.approx([0.1, 0.2, 0.3])
    assert [row.target_id for row in first] == [row.target_id for row in second]


async def _register_ab_models(
    connection: AsyncConnection,
) -> None:
    await embedding_repo.register_embedding_model(
        connection,
        EmbeddingModelCreate(model="a", model_version="v1", dim=3, is_active=True),
    )
    await embedding_repo.register_embedding_model(
        connection,
        EmbeddingModelCreate(model="b", model_version="v1", dim=3, is_active=False),
    )


async def _create_ab_embeddings(
    connection: AsyncConnection, target_id: object, scope_id: object
) -> None:
    embedding_a = EmbeddingCreate(
        target_kind="span",
        target_id=target_id,
        scope_kind="playthrough",
        scope_id=scope_id,
        model="a",
        model_version="v1",
        dim=3,
        embedding=[0.1, 0.2, 0.3],
        content_hash="hash",
    )
    embedding_b = EmbeddingCreate(
        target_kind="span",
        target_id=target_id,
        scope_kind="playthrough",
        scope_id=scope_id,
        model="b",
        model_version="v1",
        dim=3,
        embedding=[0.4, 0.5, 0.6],
        content_hash="hash",
    )
    await embedding_repo.create_embeddings(connection, [embedding_a, embedding_b])


async def _setup_multi_model_embeddings(
    connection: AsyncConnection,
) -> tuple[tuple, tuple]:
    await _register_ab_models(connection)
    target_id = uuid4()
    scope_id = uuid4()
    await _create_ab_embeddings(connection, target_id, scope_id)
    return (scope_id, "playthrough"), ("b", "v1")


async def test_list_embeddings_for_active_model_filters_by_active_model(
    db_connection: AsyncConnection,
) -> None:
    (scope_id, scope_kind), (model_b, version_b) = await _setup_multi_model_embeddings(
        db_connection
    )

    active_only = await embedding_repo.list_embeddings_for_active_model(
        db_connection, scope_kind, scope_id
    )
    assert [row.model for row in active_only] == ["a"]

    await embedding_repo.activate_embedding_model(db_connection, model_b, version_b)

    active_only = await embedding_repo.list_embeddings_for_active_model(
        db_connection, scope_kind, scope_id
    )
    assert [row.model for row in active_only] == ["b"]
