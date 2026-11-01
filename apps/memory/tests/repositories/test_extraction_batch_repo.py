"""Repository tests for app.repositories.extraction_batch_repo against a real Postgres DB."""

from uuid import uuid4

from app.models.jobs import ExtractionBatchCreate
from app.repositories import extraction_batch_repo
from psycopg import AsyncConnection


def _batch_create(**overrides: object) -> ExtractionBatchCreate:
    defaults: dict[str, object] = {
        "scope_kind": "playthrough",
        "scope_id": uuid4(),
        "from_seq": 1,
        "to_seq": 5,
        "status": "pending",
        "model": "test-model",
        "prompt_version": "v1",
        "input_hash": str(uuid4()),
    }
    defaults.update(overrides)
    return ExtractionBatchCreate(**defaults)


async def test_create_batch_idempotent(db_connection: AsyncConnection) -> None:
    batch_create = _batch_create()

    first = await extraction_batch_repo.create_batch(db_connection, batch_create)
    second = await extraction_batch_repo.create_batch(db_connection, batch_create)

    assert first.batch_id == second.batch_id


async def test_get_batch_returns_none_when_missing(
    db_connection: AsyncConnection,
) -> None:
    assert await extraction_batch_repo.get_batch(db_connection, uuid4()) is None


async def test_list_batches_filters_by_scope(db_connection: AsyncConnection) -> None:
    scope_id = uuid4()
    in_scope = await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id, from_seq=1, to_seq=5)
    )
    other_scope = await extraction_batch_repo.create_batch(
        db_connection, _batch_create(from_seq=1, to_seq=5)
    )

    rows = await extraction_batch_repo.list_batches(
        db_connection, "playthrough", scope_id, None
    )

    row_ids = {row.batch_id for row in rows}
    assert row_ids == {in_scope.batch_id}
    assert other_scope.batch_id not in row_ids


async def test_list_batches_filters_by_statuses(db_connection: AsyncConnection) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection,
        _batch_create(scope_id=scope_id, from_seq=1, to_seq=5, status="pending"),
    )
    failed = await extraction_batch_repo.create_batch(
        db_connection,
        _batch_create(scope_id=scope_id, from_seq=6, to_seq=10, status="failed"),
    )

    rows = await extraction_batch_repo.list_batches(
        db_connection, "playthrough", scope_id, ["failed"]
    )

    assert {row.batch_id for row in rows} == {failed.batch_id}


async def test_claim_pending_batch_claims_once_across_connections(
    db_connection: AsyncConnection, migrated_test_database_url: str
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    await db_connection.commit()

    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, lease_seconds=60
    )
    assert claimed is not None
    assert claimed.status == "running"
    assert claimed.attempt_count == 1

    other_connection = await AsyncConnection.connect(migrated_test_database_url)
    try:
        second_claim = await extraction_batch_repo.claim_pending_batch(
            other_connection, "playthrough", scope_id, lease_seconds=60
        )
        assert second_claim is None
    finally:
        await other_connection.rollback()
        await other_connection.close()


async def test_claim_pending_batch_returns_none_when_no_pending_batch(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()

    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, lease_seconds=60
    )

    assert claimed is None


async def test_record_batch_output_returns_none_when_not_running(
    db_connection: AsyncConnection,
) -> None:
    batch = await extraction_batch_repo.create_batch(db_connection, _batch_create())

    result = await extraction_batch_repo.record_batch_output(
        db_connection,
        batch.batch_id,
        raw_output={"ok": True},
        validated_plan={"entities": []},
        input_tokens=10,
        output_tokens=20,
    )

    assert result is None


async def test_record_batch_output_transitions_running_to_extracted(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, lease_seconds=60
    )
    assert claimed is not None

    result = await extraction_batch_repo.record_batch_output(
        db_connection,
        claimed.batch_id,
        raw_output={"ok": True},
        validated_plan={"entities": []},
        input_tokens=10,
        output_tokens=20,
    )

    assert result is not None
    assert result.status == "extracted"
    assert result.raw_output == {"ok": True}
    assert result.validated_plan == {"entities": []}


async def test_mark_batch_applied_returns_none_when_not_extracted(
    db_connection: AsyncConnection,
) -> None:
    batch = await extraction_batch_repo.create_batch(db_connection, _batch_create())

    assert (
        await extraction_batch_repo.mark_batch_applied(db_connection, batch.batch_id)
        is None
    )


async def test_mark_batch_applied_transitions_extracted_to_applied(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, lease_seconds=60
    )
    assert claimed is not None
    await extraction_batch_repo.record_batch_output(
        db_connection,
        claimed.batch_id,
        raw_output={},
        validated_plan={},
        input_tokens=1,
        output_tokens=1,
    )

    applied = await extraction_batch_repo.mark_batch_applied(
        db_connection, claimed.batch_id
    )

    assert applied is not None
    assert applied.status == "applied"


async def test_mark_batch_failed_terminal_sets_failed(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, lease_seconds=60
    )
    assert claimed is not None

    failed = await extraction_batch_repo.mark_batch_failed(
        db_connection, claimed.batch_id, error="boom", is_terminal=True
    )

    assert failed is not None
    assert failed.status == "failed"
    assert failed.error == "boom"


async def test_mark_batch_failed_retry_returns_to_pending(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, lease_seconds=60
    )
    assert claimed is not None

    retried = await extraction_batch_repo.mark_batch_failed(
        db_connection, claimed.batch_id, error="transient", is_terminal=False
    )

    assert retried is not None
    assert retried.status == "pending"


async def test_reset_failed_batches_resets_to_pending(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, lease_seconds=60
    )
    assert claimed is not None
    await extraction_batch_repo.mark_batch_failed(
        db_connection, claimed.batch_id, error="boom", is_terminal=True
    )

    reset_rows = await extraction_batch_repo.reset_failed_batches(
        db_connection, "playthrough", scope_id
    )

    assert len(reset_rows) == 1
    assert reset_rows[0].status == "pending"
    assert reset_rows[0].attempt_count == 0


DELAY_SECONDS = [60, 300, 900]


async def _age_batch(
    connection: AsyncConnection, batch_id: object, seconds: int
) -> None:
    await connection.execute(
        "UPDATE memory_extraction_batch SET updated_at = now() - make_interval(secs => %s) "
        "WHERE batch_id = %s",
        (seconds, batch_id),
    )


async def test_release_batch_returns_to_pending_without_counting_the_attempt(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, 60
    )
    assert claimed is not None and claimed.attempt_count == 1

    released = await extraction_batch_repo.release_batch(
        db_connection, claimed.batch_id
    )

    assert released is not None
    assert released.status == "pending"
    assert released.attempt_count == 0


async def test_release_expired_leases_only_frees_overdue_running_batches(
    db_connection: AsyncConnection,
) -> None:
    overdue_scope, live_scope = uuid4(), uuid4()
    for scope_id in (overdue_scope, live_scope):
        await extraction_batch_repo.create_batch(
            db_connection, _batch_create(scope_id=scope_id)
        )
    overdue = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", overdue_scope, -60
    )
    live = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", live_scope, 600
    )
    assert overdue is not None and live is not None

    released = await extraction_batch_repo.release_expired_leases(db_connection)

    assert released == 1
    after = await extraction_batch_repo.get_batch(db_connection, overdue.batch_id)
    assert after is not None and after.status == "pending"
    still_running = await extraction_batch_repo.get_batch(db_connection, live.batch_id)
    assert still_running is not None and still_running.status == "running"


async def test_due_pending_batches_respect_backoff_by_attempt_count(
    db_connection: AsyncConnection,
) -> None:
    fresh_scope, waiting_scope, elapsed_scope = uuid4(), uuid4(), uuid4()
    for scope_id in (fresh_scope, waiting_scope, elapsed_scope):
        await extraction_batch_repo.create_batch(
            db_connection, _batch_create(scope_id=scope_id)
        )
    for scope_id, age in ((waiting_scope, 10), (elapsed_scope, 120)):
        claimed = await extraction_batch_repo.claim_pending_batch(
            db_connection, "playthrough", scope_id, 60
        )
        assert claimed is not None
        await extraction_batch_repo.mark_batch_failed(
            db_connection, claimed.batch_id, "extraction_transient", is_terminal=False
        )
        await _age_batch(db_connection, claimed.batch_id, age)

    due = await extraction_batch_repo.list_due_pending_batches(
        db_connection, DELAY_SECONDS, None
    )

    assert {row.scope_id for row in due} == {fresh_scope, elapsed_scope}


async def test_due_pending_batches_can_be_scoped(
    db_connection: AsyncConnection,
) -> None:
    wanted, other = uuid4(), uuid4()
    for scope_id in (wanted, other):
        await extraction_batch_repo.create_batch(
            db_connection, _batch_create(scope_id=scope_id)
        )

    due = await extraction_batch_repo.list_due_pending_batches(
        db_connection, DELAY_SECONDS, wanted
    )

    assert [row.scope_id for row in due] == [wanted]


async def test_record_apply_failure_keeps_extracted_until_the_attempt_limit(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, 60
    )
    assert claimed is not None
    await extraction_batch_repo.record_batch_output(
        db_connection, claimed.batch_id, {}, {}, 1, 1
    )

    first = await extraction_batch_repo.record_apply_failure(
        db_connection, claimed.batch_id, 3
    )
    second = await extraction_batch_repo.record_apply_failure(
        db_connection, claimed.batch_id, 3
    )

    assert first is not None and first.status == "extracted"
    assert second is not None and second.status == "failed"
    assert second.error == "apply_failed"


async def test_due_batches_include_extracted_batches_awaiting_apply(
    db_connection: AsyncConnection,
) -> None:
    scope_id = uuid4()
    await extraction_batch_repo.create_batch(
        db_connection, _batch_create(scope_id=scope_id)
    )
    claimed = await extraction_batch_repo.claim_pending_batch(
        db_connection, "playthrough", scope_id, 60
    )
    assert claimed is not None
    await extraction_batch_repo.record_batch_output(
        db_connection, claimed.batch_id, {}, {}, 1, 1
    )

    due = await extraction_batch_repo.list_due_pending_batches(
        db_connection, DELAY_SECONDS, scope_id
    )

    assert [row.status for row in due] == ["extracted"]
