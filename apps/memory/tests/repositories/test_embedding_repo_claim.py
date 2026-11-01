"""Claim, bulk insert, coverage and cleanup queries of app.repositories.embedding_repo."""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from app.models.common import EmbeddingTargetKind, ScopeKind
from app.models.jobs import EmbeddingCreate, EmbeddingModelCreate
from app.repositories import embedding_failure_repo, embedding_repo, fact_repo
from psycopg import AsyncConnection, errors
from tests.repositories import helpers_entities, helpers_facts

MODEL_A = ("model-a", "v1")
MODEL_B = ("model-b", "v1")
DIM = 3
FAILURE_LIMIT = 3
CLAIM_LIMIT = 50
SPAN_TEXT = "test span text"


@pytest.fixture
async def models(db_connection: AsyncConnection) -> None:
    for model, version in (MODEL_A, MODEL_B):
        await embedding_repo.register_embedding_model(
            db_connection,
            EmbeddingModelCreate(
                model=model, model_version=version, dim=DIM, is_active=False
            ),
        )
    await db_connection.commit()


@pytest.fixture
async def second_connection(
    migrated_test_database_url: str,
) -> AsyncIterator[AsyncConnection]:
    connection = await AsyncConnection.connect(migrated_test_database_url)
    try:
        yield connection
    finally:
        await connection.close()


async def make_scopes(connection: AsyncConnection) -> tuple[UUID, UUID]:
    template_id = await helpers_entities.insert_template(connection)
    playthrough_id = await helpers_entities.insert_playthrough(
        connection, template_id=template_id
    )
    return template_id, playthrough_id


async def make_span(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    sequence: int = 1,
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


async def make_fact(
    connection: AsyncConnection,
    scope_kind: ScopeKind,
    scope_id: UUID,
    *,
    subject_name: str = "Mira",
    object_entity_name: str | None = None,
    object_literal: str | None = None,
    valid_from_seq: int = 1,
) -> UUID:
    subject_id = await helpers_facts.insert_entity(
        connection, scope_kind, scope_id, subject_name
    )
    object_id = None
    if object_entity_name is not None:
        object_id = await helpers_facts.insert_entity(
            connection, scope_kind, scope_id, object_entity_name
        )
    facts = await fact_repo.create_facts(
        connection,
        [
            helpers_facts.make_fact(
                scope_kind,
                scope_id,
                subject_id,
                "serves",
                object_entity_id=object_id,
                object_literal=object_literal,
                valid_from_seq=valid_from_seq,
            )
        ],
    )
    return facts[0].fact_id


def build_embedding(
    target_kind: EmbeddingTargetKind,
    target_id: UUID,
    scope_kind: ScopeKind,
    scope_id: UUID,
    model: tuple[str, str] = MODEL_A,
) -> EmbeddingCreate:
    return EmbeddingCreate(
        target_kind=target_kind,
        target_id=target_id,
        scope_kind=scope_kind,
        scope_id=scope_id,
        model=model[0],
        model_version=model[1],
        dim=DIM,
        embedding=[0.1] * DIM,
        content_hash="hash",
    )


async def claim_span_ids(
    connection: AsyncConnection,
    model: tuple[str, str] = MODEL_A,
    limit: int = CLAIM_LIMIT,
    playthrough_id: UUID | None = None,
) -> list[UUID]:
    rows = await embedding_repo.claim_unembedded_spans(
        connection, model[0], model[1], limit, FAILURE_LIMIT, playthrough_id
    )
    return [row.span_id for row in rows]


async def claim_fact_ids(
    connection: AsyncConnection,
    model: tuple[str, str] = MODEL_A,
    limit: int = CLAIM_LIMIT,
    playthrough_id: UUID | None = None,
) -> list[UUID]:
    rows = await embedding_repo.claim_unembedded_facts(
        connection, model[0], model[1], limit, FAILURE_LIMIT, playthrough_id
    )
    return [row.fact_id for row in rows]


async def test_claim_spans_orders_playthrough_before_template_then_sequence(
    db_connection: AsyncConnection, models: None
) -> None:
    template_id, playthrough_id = await make_scopes(db_connection)
    template_span = await make_span(db_connection, "template", template_id, 0)
    late_span = await make_span(db_connection, "playthrough", playthrough_id, 5)
    early_span = await make_span(db_connection, "playthrough", playthrough_id, 2)

    claimed = await embedding_repo.claim_unembedded_spans(
        db_connection, *MODEL_A, CLAIM_LIMIT, FAILURE_LIMIT, None
    )

    assert [row.span_id for row in claimed] == [early_span, late_span, template_span]
    assert claimed[0].scope_kind == "playthrough"
    assert claimed[0].scope_id == playthrough_id
    assert claimed[0].text == SPAN_TEXT
    assert claimed[2].scope_kind == "template"


async def test_claim_spans_respects_limit_and_takes_lowest_sequence(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    span_ids = [
        await make_span(db_connection, "playthrough", playthrough_id, sequence)
        for sequence in (3, 1, 2)
    ]

    claimed = await claim_span_ids(db_connection, limit=2)

    assert claimed == [span_ids[1], span_ids[2]]


async def test_claim_spans_excludes_embedded_but_reclaims_under_other_model(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    done = await make_span(db_connection, "playthrough", playthrough_id, 1)
    todo = await make_span(db_connection, "playthrough", playthrough_id, 2)
    await embedding_repo.insert_embeddings(
        db_connection,
        [build_embedding("span", done, "playthrough", playthrough_id, MODEL_A)],
    )

    assert await claim_span_ids(db_connection, MODEL_A) == [todo]
    assert await claim_span_ids(db_connection, MODEL_B) == [done, todo]


async def test_claim_spans_skips_targets_at_failure_limit_only(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    poisoned = await make_span(db_connection, "playthrough", playthrough_id, 1)
    retryable = await make_span(db_connection, "playthrough", playthrough_id, 2)
    for _ in range(FAILURE_LIMIT):
        await embedding_failure_repo.record_failures(
            db_connection, "span", [poisoned], *MODEL_A, "bad_request"
        )
    for _ in range(FAILURE_LIMIT - 1):
        await embedding_failure_repo.record_failures(
            db_connection, "span", [retryable], *MODEL_A, "bad_request"
        )

    assert await claim_span_ids(db_connection, MODEL_A) == [retryable]
    assert await claim_span_ids(db_connection, MODEL_B) == [poisoned, retryable]


async def test_claim_spans_scopes_to_playthrough_excluding_template_and_others(
    db_connection: AsyncConnection, models: None
) -> None:
    template_id, playthrough_id = await make_scopes(db_connection)
    other_playthrough_id = await helpers_entities.insert_playthrough(
        db_connection, template_id=template_id
    )
    await make_span(db_connection, "template", template_id, 0)
    await make_span(db_connection, "playthrough", other_playthrough_id, 1)
    mine = await make_span(db_connection, "playthrough", playthrough_id, 1)

    claimed = await claim_span_ids(db_connection, playthrough_id=playthrough_id)

    assert claimed == [mine]


async def test_claim_spans_skip_locked_gives_second_connection_different_rows(
    db_connection: AsyncConnection,
    second_connection: AsyncConnection,
    models: None,
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    for sequence in range(1, 5):
        await make_span(db_connection, "playthrough", playthrough_id, sequence)
    await db_connection.commit()

    first = await claim_span_ids(db_connection, limit=2)
    second = await claim_span_ids(second_connection, limit=2)

    assert len(first) == 2
    assert len(second) == 2
    assert not set(first) & set(second)


async def test_claim_spans_returns_nothing_when_every_row_is_locked(
    db_connection: AsyncConnection,
    second_connection: AsyncConnection,
    models: None,
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    for sequence in range(1, 4):
        await make_span(db_connection, "playthrough", playthrough_id, sequence)
    await db_connection.commit()

    first = await claim_span_ids(db_connection)
    second = await claim_span_ids(second_connection)

    assert len(first) == 3
    assert second == []


async def test_claim_facts_orders_playthrough_first_then_valid_from_and_scopes(
    db_connection: AsyncConnection, models: None
) -> None:
    template_id, playthrough_id = await make_scopes(db_connection)
    other_playthrough_id = await helpers_entities.insert_playthrough(
        db_connection, template_id=template_id
    )
    template_fact = await make_fact(
        db_connection, "template", template_id, valid_from_seq=0
    )
    late = await make_fact(
        db_connection, "playthrough", playthrough_id, valid_from_seq=4
    )
    early = await make_fact(
        db_connection, "playthrough", playthrough_id, valid_from_seq=2
    )
    await make_fact(db_connection, "playthrough", other_playthrough_id)

    unscoped = await claim_fact_ids(db_connection)
    assert unscoped[-1] == template_fact
    assert unscoped.index(early) < unscoped.index(late) < unscoped.index(template_fact)
    assert len(await claim_fact_ids(db_connection, limit=2)) == 2
    assert await claim_fact_ids(db_connection, playthrough_id=playthrough_id) == [
        early,
        late,
    ]


async def test_claim_facts_resolves_names_preferring_entity_over_literal(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    both = await make_fact(
        db_connection,
        "playthrough",
        playthrough_id,
        subject_name="Mira",
        object_entity_name="Red Guild",
        object_literal="ignored literal",
        valid_from_seq=1,
    )
    literal = await make_fact(
        db_connection,
        "playthrough",
        playthrough_id,
        subject_name="Tor",
        object_literal="a golden key",
        valid_from_seq=2,
    )
    bare = await make_fact(
        db_connection,
        "playthrough",
        playthrough_id,
        subject_name="Lys",
        valid_from_seq=3,
    )

    rows = await embedding_repo.claim_unembedded_facts(
        db_connection, *MODEL_A, CLAIM_LIMIT, FAILURE_LIMIT, None
    )

    by_id = {row.fact_id: row for row in rows}
    assert [row.fact_id for row in rows] == [both, literal, bare]
    assert by_id[both].subject_name == "Mira"
    assert by_id[both].predicate == "serves"
    assert by_id[both].object_text == "Red Guild"
    assert by_id[both].scope_kind == "playthrough"
    assert by_id[both].scope_id == playthrough_id
    assert by_id[literal].object_text == "a golden key"
    assert by_id[bare].object_text is None


async def test_claim_facts_excludes_embedded_and_failure_limited(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    embedded = await make_fact(
        db_connection, "playthrough", playthrough_id, valid_from_seq=1
    )
    poisoned = await make_fact(
        db_connection, "playthrough", playthrough_id, valid_from_seq=2
    )
    todo = await make_fact(
        db_connection, "playthrough", playthrough_id, valid_from_seq=3
    )
    await embedding_repo.insert_embeddings(
        db_connection,
        [build_embedding("fact", embedded, "playthrough", playthrough_id)],
    )
    for _ in range(FAILURE_LIMIT):
        await embedding_failure_repo.record_failures(
            db_connection, "fact", [poisoned], *MODEL_A, "bad_request"
        )

    assert await claim_fact_ids(db_connection, MODEL_A) == [todo]
    assert await claim_fact_ids(db_connection, MODEL_B) == [embedded, poisoned, todo]


async def test_claim_facts_skip_locked_gives_second_connection_different_rows(
    db_connection: AsyncConnection,
    second_connection: AsyncConnection,
    models: None,
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    for sequence in range(1, 4):
        await make_fact(
            db_connection, "playthrough", playthrough_id, valid_from_seq=sequence
        )
    await db_connection.commit()

    first = await claim_fact_ids(db_connection, limit=2)
    second = await claim_fact_ids(second_connection)
    third = await claim_fact_ids(second_connection)

    assert len(first) == 2
    assert len(second) == 1
    assert not set(first) & set(second)
    assert third == second


async def test_insert_embeddings_bulk_inserts_and_is_idempotent(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    span_ids = [
        await make_span(db_connection, "playthrough", playthrough_id, sequence)
        for sequence in range(1, 4)
    ]
    fact_id = await make_fact(db_connection, "playthrough", playthrough_id)
    batch = [
        build_embedding("span", span_id, "playthrough", playthrough_id)
        for span_id in span_ids
    ]
    batch.append(build_embedding("fact", fact_id, "playthrough", playthrough_id))

    first = await embedding_repo.insert_embeddings(db_connection, batch)
    second = await embedding_repo.insert_embeddings(db_connection, batch)

    cursor = await db_connection.execute("SELECT count(*) FROM memory_embedding")
    count_row = await cursor.fetchone()
    assert (first, second) == (4, 0)
    assert count_row is not None and count_row[0] == 4


async def test_insert_embeddings_counts_only_new_rows_and_handles_empty(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    existing = await make_span(db_connection, "playthrough", playthrough_id, 1)
    fresh = await make_span(db_connection, "playthrough", playthrough_id, 2)
    await embedding_repo.insert_embeddings(
        db_connection,
        [build_embedding("span", existing, "playthrough", playthrough_id)],
    )

    inserted = await embedding_repo.insert_embeddings(
        db_connection,
        [
            build_embedding("span", existing, "playthrough", playthrough_id),
            build_embedding("span", fresh, "playthrough", playthrough_id),
        ],
    )

    assert inserted == 1
    assert await embedding_repo.insert_embeddings(db_connection, []) == 0


async def test_insert_embeddings_rejects_dimension_mismatch_and_unknown_model(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    span_id = await make_span(db_connection, "playthrough", playthrough_id, 1)
    await db_connection.commit()
    wrong_dim = build_embedding(
        "span", span_id, "playthrough", playthrough_id
    ).model_copy(update={"embedding": [0.1, 0.2]})
    unknown_model = build_embedding(
        "span", span_id, "playthrough", playthrough_id, ("ghost", "v9")
    )

    with pytest.raises(errors.CheckViolation):
        await embedding_repo.insert_embeddings(db_connection, [wrong_dim])
    await db_connection.rollback()
    with pytest.raises(errors.ForeignKeyViolation):
        await embedding_repo.insert_embeddings(db_connection, [unknown_model])


async def test_count_uncovered_targets_reaches_zero_as_coverage_completes(
    db_connection: AsyncConnection, models: None
) -> None:
    template_id, playthrough_id = await make_scopes(db_connection)
    span_id = await make_span(db_connection, "playthrough", playthrough_id, 1)
    template_span = await make_span(db_connection, "template", template_id, 0)
    fact_id = await make_fact(db_connection, "playthrough", playthrough_id)

    async def count_uncovered(model: tuple[str, str]) -> int:
        return await embedding_repo.count_uncovered_targets(
            db_connection, model[0], model[1], FAILURE_LIMIT
        )

    assert await count_uncovered(MODEL_A) == 3
    await embedding_repo.insert_embeddings(
        db_connection,
        [build_embedding("span", span_id, "playthrough", playthrough_id)],
    )
    assert await count_uncovered(MODEL_A) == 2
    assert await count_uncovered(MODEL_B) == 3
    for _ in range(FAILURE_LIMIT):
        await embedding_failure_repo.record_failures(
            db_connection, "span", [template_span], *MODEL_A, "bad_request"
        )
    assert await count_uncovered(MODEL_A) == 1
    await embedding_repo.insert_embeddings(
        db_connection,
        [build_embedding("fact", fact_id, "playthrough", playthrough_id)],
    )
    assert await count_uncovered(MODEL_A) == 0


async def test_delete_embeddings_except_models_keeps_listed_models_only(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    await embedding_repo.register_embedding_model(
        db_connection,
        EmbeddingModelCreate(model="old", model_version="v0", dim=DIM, is_active=False),
    )
    span_id = await make_span(db_connection, "playthrough", playthrough_id, 1)
    for model in (MODEL_A, MODEL_B, ("old", "v0")):
        await embedding_repo.insert_embeddings(
            db_connection,
            [build_embedding("span", span_id, "playthrough", playthrough_id, model)],
        )

    deleted = await embedding_repo.delete_embeddings_except_models(
        db_connection, [MODEL_A, MODEL_B]
    )

    cursor = await db_connection.execute(
        "SELECT model FROM memory_embedding ORDER BY model"
    )
    remaining = [row[0] for row in await cursor.fetchall()]
    assert deleted == 1
    assert remaining == ["model-a", "model-b"]


async def test_delete_embeddings_except_models_with_empty_keep_list_deletes_nothing(
    db_connection: AsyncConnection, models: None
) -> None:
    _, playthrough_id = await make_scopes(db_connection)
    span_id = await make_span(db_connection, "playthrough", playthrough_id, 1)
    await embedding_repo.insert_embeddings(
        db_connection,
        [build_embedding("span", span_id, "playthrough", playthrough_id)],
    )

    deleted = await embedding_repo.delete_embeddings_except_models(db_connection, [])

    cursor = await db_connection.execute("SELECT count(*) FROM memory_embedding")
    count_row = await cursor.fetchone()
    assert deleted == 0
    assert count_row is not None and count_row[0] == 1
