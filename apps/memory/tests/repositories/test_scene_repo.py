"""Repository tests for app.repositories.scene_repo against a real Postgres DB."""

from uuid import UUID, uuid4

from app.models.facts import SceneStateCreate
from app.models.jobs import ExtractionBatchCreate
from app.repositories import extraction_batch_repo, scene_repo
from psycopg import AsyncConnection
from tests.repositories.helpers_entities import insert_playthrough


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


async def test_append_scene_state_idempotent(db_connection: AsyncConnection) -> None:
    playthrough_id = await insert_playthrough(db_connection)
    batch_id = await _create_batch(db_connection, playthrough_id)
    scene = SceneStateCreate(
        playthrough_id=playthrough_id,
        valid_from_seq=1,
        present_entity_ids=[],
        extraction_batch_id=batch_id,
    )

    first = await scene_repo.append_scene_state(db_connection, scene)
    second = await scene_repo.append_scene_state(db_connection, scene)

    assert first == second


async def _setup_scene_states(
    connection: AsyncConnection,
) -> UUID:
    playthrough_id = await insert_playthrough(connection)
    batch_id = await _create_batch(connection, playthrough_id)
    await scene_repo.append_scene_state(
        connection,
        SceneStateCreate(
            playthrough_id=playthrough_id,
            valid_from_seq=1,
            present_entity_ids=[],
            extraction_batch_id=batch_id,
        ),
    )
    await scene_repo.append_scene_state(
        connection,
        SceneStateCreate(
            playthrough_id=playthrough_id,
            valid_from_seq=8,
            present_entity_ids=[],
            extraction_batch_id=batch_id,
        ),
    )
    return playthrough_id


async def test_get_scene_at_returns_latest_state_at_or_before_n(
    db_connection: AsyncConnection,
) -> None:
    playthrough_id = await _setup_scene_states(db_connection)

    at_0 = await scene_repo.get_scene_at(db_connection, playthrough_id, 0)
    at_5 = await scene_repo.get_scene_at(db_connection, playthrough_id, 5)
    at_8 = await scene_repo.get_scene_at(db_connection, playthrough_id, 8)

    assert at_0 is None
    assert at_5 is not None
    assert at_5.valid_from_seq == 1
    assert at_8 is not None
    assert at_8.valid_from_seq == 8


async def test_get_scene_at_scope_isolation_by_playthrough(
    db_connection: AsyncConnection,
) -> None:
    playthrough_a = await insert_playthrough(db_connection)
    playthrough_b = await insert_playthrough(db_connection)
    batch_a = await _create_batch(db_connection, playthrough_a)
    await scene_repo.append_scene_state(
        db_connection,
        SceneStateCreate(
            playthrough_id=playthrough_a,
            valid_from_seq=1,
            present_entity_ids=[],
            extraction_batch_id=batch_a,
        ),
    )

    assert await scene_repo.get_scene_at(db_connection, playthrough_b, 1) is None
