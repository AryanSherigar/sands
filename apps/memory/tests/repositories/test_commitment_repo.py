"""Repository tests for app.repositories.commitment_repo against a real Postgres DB."""

from uuid import UUID, uuid4

from app.models.facts import CommitmentCreate, CommitmentStatusCreate, EntityCreate
from app.models.jobs import ExtractionBatchCreate
from app.repositories import commitment_repo, entity_repo, extraction_batch_repo
from psycopg import AsyncConnection
from tests.repositories.helpers_entities import (
    insert_playthrough,
    insert_source,
    insert_span,
)


async def _create_owner_entity(connection: AsyncConnection, scope_id: UUID) -> UUID:
    entity = await entity_repo.create_entity(
        connection,
        EntityCreate(
            scope_kind="playthrough",
            scope_id=scope_id,
            entity_type="npc",
            canonical_name="Owner",
            provenance="extracted",
            first_seen_seq=1,
        ),
    )
    return entity.entity_id


async def _create_batch(connection: AsyncConnection, scope_id: UUID) -> UUID:
    batch = await extraction_batch_repo.create_batch(
        connection,
        ExtractionBatchCreate(
            scope_kind="playthrough",
            scope_id=scope_id,
            from_seq=1,
            to_seq=5,
            status="pending",
            model="test-model",
            prompt_version="v1",
            input_hash=str(uuid4()),
        ),
    )
    return batch.batch_id


async def _setup_commitment_prereqs(
    connection: AsyncConnection,
) -> tuple[UUID, UUID, UUID, UUID]:
    playthrough_id = await insert_playthrough(connection)
    source_id = await insert_source(
        connection, scope_kind="playthrough", scope_id=playthrough_id
    )
    span_id = await insert_span(
        connection,
        source_id=source_id,
        scope_kind="playthrough",
        scope_id=playthrough_id,
    )
    owner_entity_id = await _create_owner_entity(connection, playthrough_id)
    batch_id = await _create_batch(connection, playthrough_id)
    return playthrough_id, owner_entity_id, span_id, batch_id


async def _create_debt_commitment(
    connection: AsyncConnection,
    playthrough_id: UUID,
    owner_entity_id: UUID,
    span_id: UUID,
    batch_id: UUID,
) -> object:
    return await commitment_repo.create_commitment(
        connection,
        CommitmentCreate(
            playthrough_id=playthrough_id,
            kind="debt",
            owner_entity_id=owner_entity_id,
            summary="Owes 50 gold",
            opened_seq=3,
            opening_span_id=span_id,
            extraction_batch_id=batch_id,
        ),
    )


async def _append_commitment_statuses(
    connection: AsyncConnection, commitment_id: UUID
) -> None:
    await commitment_repo.append_commitment_status(
        connection,
        CommitmentStatusCreate(commitment_id=commitment_id, at_seq=3, status="open"),
    )
    await commitment_repo.append_commitment_status(
        connection,
        CommitmentStatusCreate(
            commitment_id=commitment_id, at_seq=10, status="fulfilled"
        ),
    )


async def test_create_commitment_returns_row(db_connection: AsyncConnection) -> None:
    (
        playthrough_id,
        owner_entity_id,
        span_id,
        batch_id,
    ) = await _setup_commitment_prereqs(db_connection)

    commitment = await commitment_repo.create_commitment(
        db_connection,
        CommitmentCreate(
            playthrough_id=playthrough_id,
            kind="promise",
            owner_entity_id=owner_entity_id,
            summary="Bring the sword back",
            opened_seq=3,
            opening_span_id=span_id,
            extraction_batch_id=batch_id,
        ),
    )

    assert commitment.kind == "promise"
    assert commitment.opened_seq == 3


async def test_append_commitment_status_idempotent(
    db_connection: AsyncConnection,
) -> None:
    (
        playthrough_id,
        owner_entity_id,
        span_id,
        batch_id,
    ) = await _setup_commitment_prereqs(db_connection)
    commitment = await commitment_repo.create_commitment(
        db_connection,
        CommitmentCreate(
            playthrough_id=playthrough_id,
            kind="quest",
            owner_entity_id=owner_entity_id,
            summary="Defeat the dragon",
            opened_seq=1,
            opening_span_id=span_id,
            extraction_batch_id=batch_id,
        ),
    )
    status = CommitmentStatusCreate(
        commitment_id=commitment.commitment_id, at_seq=5, status="open"
    )

    first = await commitment_repo.append_commitment_status(db_connection, status)
    second = await commitment_repo.append_commitment_status(db_connection, status)

    assert first == second


async def test_list_commitments_at_returns_latest_status_at_or_before_n(
    db_connection: AsyncConnection,
) -> None:
    (
        playthrough_id,
        owner_entity_id,
        span_id,
        batch_id,
    ) = await _setup_commitment_prereqs(db_connection)
    commitment = await _create_debt_commitment(
        db_connection, playthrough_id, owner_entity_id, span_id, batch_id
    )
    await _append_commitment_statuses(db_connection, commitment.commitment_id)

    at_2 = await commitment_repo.list_commitments_at(db_connection, playthrough_id, 2)
    at_5 = await commitment_repo.list_commitments_at(db_connection, playthrough_id, 5)
    at_10 = await commitment_repo.list_commitments_at(db_connection, playthrough_id, 10)

    assert at_2 == []
    assert len(at_5) == 1
    assert at_5[0][1] is not None
    assert at_5[0][1].status == "open"
    assert at_10[0][1] is not None
    assert at_10[0][1].status == "fulfilled"


async def test_list_commitments_at_with_no_status_returns_none_status(
    db_connection: AsyncConnection,
) -> None:
    (
        playthrough_id,
        owner_entity_id,
        span_id,
        batch_id,
    ) = await _setup_commitment_prereqs(db_connection)
    await commitment_repo.create_commitment(
        db_connection,
        CommitmentCreate(
            playthrough_id=playthrough_id,
            kind="threat",
            owner_entity_id=owner_entity_id,
            summary="A shadow looms",
            opened_seq=1,
            opening_span_id=span_id,
            extraction_batch_id=batch_id,
        ),
    )

    rows = await commitment_repo.list_commitments_at(db_connection, playthrough_id, 5)

    assert len(rows) == 1
    assert rows[0][1] is None
