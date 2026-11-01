"""Repository tests for app.repositories.embedding_failure_repo against a real Postgres DB."""

from uuid import uuid4

import psycopg
import pytest
from app.repositories import embedding_failure_repo
from psycopg import AsyncConnection

MODEL = "text-embed"
MODEL_VERSION = "v1"
ERROR_CODE = "embedding_permanent_error"
LARGE_BATCH_SIZE = 500


async def test_first_record_inserts_attempt_count_one(
    db_connection: AsyncConnection,
) -> None:
    target_id = uuid4()

    rows = await embedding_failure_repo.record_failures(
        db_connection, "span", [target_id], MODEL, MODEL_VERSION, ERROR_CODE
    )

    assert len(rows) == 1
    assert rows[0].target_kind == "span"
    assert rows[0].target_id == target_id
    assert rows[0].attempt_count == 1


async def test_repeat_record_increments_attempt_count(
    db_connection: AsyncConnection,
) -> None:
    target_id = uuid4()
    for _ in range(2):
        await embedding_failure_repo.record_failures(
            db_connection, "fact", [target_id], MODEL, MODEL_VERSION, ERROR_CODE
        )

    rows = await embedding_failure_repo.record_failures(
        db_connection, "fact", [target_id], MODEL, MODEL_VERSION, ERROR_CODE
    )

    assert rows[0].attempt_count == 3


async def test_error_code_is_stored_and_replaced_on_repeat(
    db_connection: AsyncConnection,
) -> None:
    target_id = uuid4()
    first = await embedding_failure_repo.record_failures(
        db_connection, "span", [target_id], MODEL, MODEL_VERSION, "first_code"
    )
    second = await embedding_failure_repo.record_failures(
        db_connection, "span", [target_id], MODEL, MODEL_VERSION, "second_code"
    )

    assert first[0].last_error == "first_code"
    assert second[0].last_error == "second_code"
    assert second[0].updated_at >= first[0].updated_at


async def test_different_model_and_version_are_tracked_separately(
    db_connection: AsyncConnection,
) -> None:
    target_id = uuid4()
    await embedding_failure_repo.record_failures(
        db_connection, "span", [target_id], MODEL, "v1", ERROR_CODE
    )
    await embedding_failure_repo.record_failures(
        db_connection, "span", [target_id], MODEL, "v1", ERROR_CODE
    )
    await embedding_failure_repo.record_failures(
        db_connection, "span", [target_id], MODEL, "v2", ERROR_CODE
    )
    await embedding_failure_repo.record_failures(
        db_connection, "span", [target_id], "other-model", "v1", ERROR_CODE
    )

    assert await embedding_failure_repo.get_failure_counts(
        db_connection, "span", [target_id], MODEL, "v1"
    ) == {target_id: 2}
    assert await embedding_failure_repo.get_failure_counts(
        db_connection, "span", [target_id], MODEL, "v2"
    ) == {target_id: 1}
    assert await embedding_failure_repo.get_failure_counts(
        db_connection, "span", [target_id], "other-model", "v1"
    ) == {target_id: 1}


async def test_same_id_with_different_target_kind_is_tracked_separately(
    db_connection: AsyncConnection,
) -> None:
    target_id = uuid4()
    await embedding_failure_repo.record_failures(
        db_connection, "span", [target_id], MODEL, MODEL_VERSION, ERROR_CODE
    )

    assert (
        await embedding_failure_repo.get_failure_counts(
            db_connection, "fact", [target_id], MODEL, MODEL_VERSION
        )
        == {}
    )


async def test_counts_for_absent_ids_are_missing_from_result(
    db_connection: AsyncConnection,
) -> None:
    recorded_id, absent_id = uuid4(), uuid4()
    await embedding_failure_repo.record_failures(
        db_connection, "span", [recorded_id], MODEL, MODEL_VERSION, ERROR_CODE
    )

    counts = await embedding_failure_repo.get_failure_counts(
        db_connection, "span", [recorded_id, absent_id], MODEL, MODEL_VERSION
    )

    assert counts == {recorded_id: 1}
    assert absent_id not in counts


async def test_counts_for_empty_id_list_is_empty(
    db_connection: AsyncConnection,
) -> None:
    assert (
        await embedding_failure_repo.get_failure_counts(
            db_connection, "span", [], MODEL, MODEL_VERSION
        )
        == {}
    )


async def test_record_with_empty_id_list_writes_nothing(
    db_connection: AsyncConnection,
) -> None:
    rows = await embedding_failure_repo.record_failures(
        db_connection, "span", [], MODEL, MODEL_VERSION, ERROR_CODE
    )

    assert rows == []


async def test_batch_of_many_ids_is_recorded_in_one_call(
    db_connection: AsyncConnection,
) -> None:
    target_ids = [uuid4() for _ in range(LARGE_BATCH_SIZE)]

    rows = await embedding_failure_repo.record_failures(
        db_connection, "fact", target_ids, MODEL, MODEL_VERSION, ERROR_CODE
    )
    await embedding_failure_repo.record_failures(
        db_connection, "fact", target_ids[:10], MODEL, MODEL_VERSION, ERROR_CODE
    )
    counts = await embedding_failure_repo.get_failure_counts(
        db_connection, "fact", target_ids, MODEL, MODEL_VERSION
    )

    assert {row.target_id for row in rows} == set(target_ids)
    assert len(counts) == LARGE_BATCH_SIZE
    assert all(counts[target_id] == 2 for target_id in target_ids[:10])
    assert all(counts[target_id] == 1 for target_id in target_ids[10:])


async def test_duplicate_ids_in_one_call_increment_once(
    db_connection: AsyncConnection,
) -> None:
    target_id = uuid4()

    rows = await embedding_failure_repo.record_failures(
        db_connection,
        "span",
        [target_id, target_id],
        MODEL,
        MODEL_VERSION,
        ERROR_CODE,
    )

    assert len(rows) == 1
    assert rows[0].attempt_count == 1


async def test_negative_attempt_count_violates_check(
    db_connection: AsyncConnection,
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        await db_connection.execute(
            "INSERT INTO memory_embedding_failure "
            "(target_kind, target_id, model, model_version, attempt_count) "
            "VALUES ('span', %s, %s, %s, -1)",
            (uuid4(), MODEL, MODEL_VERSION),
        )


async def test_unknown_target_kind_violates_check(
    db_connection: AsyncConnection,
) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        await db_connection.execute(
            "INSERT INTO memory_embedding_failure "
            "(target_kind, target_id, model, model_version) VALUES ('other', %s, %s, %s)",
            (uuid4(), MODEL, MODEL_VERSION),
        )
