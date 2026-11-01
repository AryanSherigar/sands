"""Gated live smoke of retrieval against the real Vertex AI embedding endpoint (spends money).

Run: pytest -m live_embedding -s tests/live/test_live_retrieval.py
Skipped when GOOGLE_CLOUD_API_KEY is in neither the repo-root .env nor the process env.
"""

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from app.models.retrieve import RetrieveRequest
from app.services.indexing_service import IndexingService
from app.services.retrieval_service import RetrievalService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.live.test_live_embedding import (
    API_KEY,
    LIVE_DIM,
    LIVE_MODEL_NAME,
    LIVE_MODEL_VERSION,
    POOL_MAX_SIZE,
    QUERY_TEXT,
    SELECT_ACTIVE_MODEL_SQL,
    SELECT_MEMORY_TABLES_SQL,
    SMALL_TURN_COUNT,
    _build_small_playthrough,
    _live_client,
    _live_settings,
    _run_sweeps,
)

if not API_KEY:
    pytest.skip("GOOGLE_CLOUD_API_KEY not available", allow_module_level=True)

pytestmark = pytest.mark.live_embedding

RETRIEVE_SEQUENCE = SMALL_TURN_COUNT + 1
NO_RECENT_WINDOW = 0
# NOTE: the production 300 ms sub-budget is a latency gate, measured by the report-only
# script; this smoke proves the vector path works, so it allows a realistic round trip.
LIVE_EMBED_TIMEOUT_SECONDS = 10.0


class RecordingQueryEmbedder:
    """Wraps the real query embedder and remembers the dimensions it returned."""

    def __init__(self, embed_query: object) -> None:
        self._embed_query = embed_query
        self.dimensions: list[int] = []

    async def __call__(self, text: str) -> list[float]:
        vector: list[float] = await self._embed_query(text)  # type: ignore[operator]
        self.dimensions.append(len(vector))
        return vector


@pytest.fixture
async def connection(db_connection: AsyncConnection) -> AsyncIterator[AsyncConnection]:
    yield db_connection
    await db_connection.rollback()
    cursor = await db_connection.execute(SELECT_MEMORY_TABLES_SQL)
    names = [f'"{row[0]}"' for row in await cursor.fetchall()]
    await db_connection.execute(f"TRUNCATE {', '.join(names)} RESTART IDENTITY CASCADE")
    await db_connection.commit()


@pytest.fixture
async def pool(
    migrated_test_database_url: str, connection: AsyncConnection
) -> AsyncIterator[AsyncConnectionPool]:
    connection_pool = AsyncConnectionPool(
        migrated_test_database_url, min_size=1, max_size=POOL_MAX_SIZE, open=False
    )
    await connection_pool.open()
    yield connection_pool
    await connection_pool.close()


def _build_request(playthrough_id: UUID) -> RetrieveRequest:
    return RetrieveRequest(
        playthrough_id=playthrough_id,
        sequence=RETRIEVE_SEQUENCE,
        action_text=QUERY_TEXT,
        action_mode="say",
        actor_participant_id=uuid4(),
        recent_text="",
        recent_window_turns=NO_RECENT_WINDOW,
    )


async def test_real_query_embedding_drives_the_vector_branch(
    pool: AsyncConnectionPool, connection: AsyncConnection
) -> None:
    settings = _live_settings().model_copy(
        update={"retrieval_embed_timeout_seconds": LIVE_EMBED_TIMEOUT_SECONDS}
    )
    client = _live_client(settings)
    playthrough_id = await _build_small_playthrough(connection)
    await _run_sweeps(IndexingService(pool, settings, client))
    embedder = RecordingQueryEmbedder(client.embed_query)
    service = RetrievalService(pool, settings, embedder)

    response = await service.retrieve(_build_request(playthrough_id))

    active = await connection.execute(SELECT_ACTIVE_MODEL_SQL)
    assert await active.fetchall() == [(LIVE_MODEL_NAME, LIVE_MODEL_VERSION, LIVE_DIM)]
    assert response.embedding_model == LIVE_MODEL_NAME
    assert embedder.dimensions == [LIVE_DIM]
    assert "vector" not in response.skipped_branches
    assert any("vector" in item.branches for item in response.items)
    print(f"\nlive retrieval: {len(response.items)} items, {response.watermarks}")
