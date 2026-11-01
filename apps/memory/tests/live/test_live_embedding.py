"""Gated live smoke against the real Vertex AI embedding endpoint (spends money).

Run: pytest -m live_embedding -s tests/live
Skipped when GOOGLE_CLOUD_API_KEY is in neither the repo-root .env nor the process env.
"""

import asyncio
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.config import Settings
from app.integrations.embedding_client import EmbeddingClient
from app.models.ingest import IngestRequest
from app.models.process_pending import ProcessPendingRequest
from app.models.templates import StoryCardPayload
from app.services.indexing_service import IndexingService
from app.services.ingest_service import IngestService
from app.services.template_service import TemplateService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services.ingest_helpers import (
    TurnSpec,
    build_request,
    register_item,
    turn_item,
)
from tests.services.template_helpers import (
    build_hollow_cairn,
    build_newbie_request,
    story_card,
)

API_KEY_NAME = "GOOGLE_CLOUD_API_KEY"
LIVE_ENV_FILE_VARIABLE = "LIVE_ENV_FILE"
REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"
LIVE_MODEL_NAME = "text-embedding-005"
LIVE_MODEL_VERSION = "1"
LIVE_DIM = 768
CLIENT_TIMEOUT_SECONDS = 30
TRANSIENT_RETRIES = 3
SWEEP_DEADLINE_SECONDS = 45
MAX_SWEEPS = 40
RATE_LIMIT_PAUSE_SECONDS = 20
CONCURRENCY_VARIABLE = "LIVE_EMBEDDING_CONCURRENCY"
BATCH_SIZE_VARIABLE = "LIVE_EMBEDDING_BATCH_SIZE"
DEFAULT_LIVE_CONCURRENCY = 4
DEFAULT_LIVE_BATCH_SIZE = 100
POOL_MAX_SIZE = 12
SMALL_TURN_COUNT = 6
PUBLISH_REVISION = 1
LORE_PARAGRAPH_COUNT = 3000
WORDS_PER_PARAGRAPH = 100
CARD_COUNT = 50
DONE_STEPS = ("completed", "idle")
LORE_WORDS = (
    "river",
    "ferrymen",
    "villages",
    "ember",
    "lantern",
    "orchard",
    "salt",
    "granite",
    "tide",
    "wolves",
    "harvest",
    "chapel",
    "bridge",
    "winter",
    "smoke",
)
SAMPLE_TEXTS = [
    "The warden guards the hollow cairn at the edge of Ashfall.",
    "Kestrel lights a lantern and descends the barrow stairs.",
    "A ledger of unpaid tithes lies rotting in the vigil hall.",
    "Rain over the salt marsh, and no ferry until dawn.",
]
QUERY_TEXT = "Who watches over the burial mound?"

COUNT_SPANS_SQL = "SELECT count(*) FROM memory_span"
COUNT_FACTS_SQL = "SELECT count(*) FROM memory_fact"
COUNT_EMBEDDINGS_SQL = "SELECT count(*) FROM memory_embedding"
COUNT_WRONG_DIM_SQL = "SELECT count(*) FROM memory_embedding WHERE dim <> %s"
COUNT_FAILURES_SQL = "SELECT count(*) FROM memory_embedding_failure"
SELECT_ACTIVE_MODEL_SQL = (
    "SELECT model, model_version, dim FROM memory_embedding_model WHERE is_active"
)
SELECT_INDEXED_SEQ_SQL = (
    "SELECT ingested_seq, indexed_seq FROM memory_playthrough WHERE playthrough_id = %s"
)
SELECT_MEMORY_TABLES_SQL = (
    "SELECT tablename FROM pg_tables "
    "WHERE schemaname = 'public' AND tablename LIKE 'memory\\_%'"
)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _separator, raw_value = stripped.partition("=")
        values[name.strip()] = raw_value.strip().strip("'\"")
    return values


def _resolve_api_key() -> str:
    env_file = Path(os.environ.get(LIVE_ENV_FILE_VARIABLE) or REPO_ROOT_ENV_FILE)
    from_file = _parse_env_file(env_file).get(API_KEY_NAME, "")
    return from_file or os.environ.get(API_KEY_NAME, "")


API_KEY = _resolve_api_key()
if not API_KEY:
    pytest.skip(f"{API_KEY_NAME} not available", allow_module_level=True)

pytestmark = pytest.mark.live_embedding


def _live_settings() -> Settings:
    return Settings(
        embedding_api_key=API_KEY,
        embedding_model_name=LIVE_MODEL_NAME,
        embedding_model_version=LIVE_MODEL_VERSION,
        embedding_dim=LIVE_DIM,
        embedding_client_timeout_seconds=CLIENT_TIMEOUT_SECONDS,
        embedding_transient_retries=TRANSIENT_RETRIES,
        embedding_concurrency=int(
            os.environ.get(CONCURRENCY_VARIABLE, DEFAULT_LIVE_CONCURRENCY)
        ),
        embedding_batch_size=int(
            os.environ.get(BATCH_SIZE_VARIABLE, DEFAULT_LIVE_BATCH_SIZE)
        ),
    )


def _live_client(settings: Settings) -> EmbeddingClient:
    return EmbeddingClient(
        api_key=settings.embedding_api_key,
        model_name=settings.embedding_model_name,
        dim=settings.embedding_dim,
        timeout_seconds=settings.embedding_client_timeout_seconds,
        transient_retries=settings.embedding_transient_retries,
    )


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


async def _scalar(
    connection: AsyncConnection, statement: str, *parameters: object
) -> int:
    cursor = await connection.execute(statement, parameters or None)
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


def _vectors_are_distinct(vectors: list[list[float]]) -> bool:
    return len({tuple(vector) for vector in vectors}) == len(vectors)


async def _run_sweeps(
    service: IndexingService, playthrough_id: UUID | None = None
) -> tuple[int, int, int]:
    """Returns (sweeps, targets embedded, characters embedded)."""
    request = ProcessPendingRequest(
        playthrough_id=playthrough_id, deadline_seconds=SWEEP_DEADLINE_SECONDS
    )
    targets = characters = rate_limited_sweeps = 0
    for sweep_number in range(1, MAX_SWEEPS + 1):
        response = await service.process_pending(request)
        targets += response.counts.spans_embedded + response.counts.facts_embedded
        characters += response.counts.characters_embedded
        if response.embedding_step == "rate_limited":
            rate_limited_sweeps += 1
            await asyncio.sleep(RATE_LIMIT_PAUSE_SECONDS)
            continue
        assert response.embedding_step in (*DONE_STEPS, "deadline_reached"), (
            response.embedding_step,
            response.errors,
        )
        if response.embedding_step in DONE_STEPS:
            print(
                f"live sweeps={sweep_number} rate_limited_sweeps={rate_limited_sweeps}"
            )
            return sweep_number, targets, characters
    pytest.fail(f"indexing did not complete within {MAX_SWEEPS} sweeps")


async def _assert_fully_embedded(connection: AsyncConnection) -> int:
    span_count = await _scalar(connection, COUNT_SPANS_SQL)
    fact_count = await _scalar(connection, COUNT_FACTS_SQL)
    assert span_count + fact_count > 0
    assert await _scalar(connection, COUNT_EMBEDDINGS_SQL) == span_count + fact_count
    assert await _scalar(connection, COUNT_WRONG_DIM_SQL, LIVE_DIM) == 0
    assert await _scalar(connection, COUNT_FAILURES_SQL) == 0
    return span_count + fact_count


async def _build_small_playthrough(connection: AsyncConnection) -> UUID:
    hollow_cairn = build_hollow_cairn(publish_revision=PUBLISH_REVISION)
    await TemplateService(connection).build_template(hollow_cairn.request)
    await connection.commit()
    playthrough_id = uuid4()
    items = [
        register_item(
            hollow_cairn.request.scenario_id, publish_revision=PUBLISH_REVISION
        )
    ]
    for sequence in range(1, SMALL_TURN_COUNT + 1):
        spec = TurnSpec(
            sequence=sequence,
            action=f"Kestrel searches chamber {sequence} of the cairn.",
            narration=(
                f"Torchlight crawls over the wet stone of chamber {sequence}, "
                f"and the Warden's breathing echoes {sequence} paces behind."
            ),
        )
        items.append(turn_item(spec))
    request: IngestRequest = build_request(playthrough_id, *items)
    await IngestService(connection).ingest_items(request)
    await connection.commit()
    return playthrough_id


def _build_lore() -> str:
    paragraphs = []
    for paragraph_index in range(LORE_PARAGRAPH_COUNT):
        words = [
            LORE_WORDS[(paragraph_index * 7 + word_index) % len(LORE_WORDS)]
            for word_index in range(WORDS_PER_PARAGRAPH)
        ]
        paragraphs.append(f"Chronicle {paragraph_index}: " + " ".join(words))
    return "\n\n".join(paragraphs)


def _build_cards() -> list[StoryCardPayload]:
    return [
        story_card(
            f"card-{index}",
            f"Card Person {index}",
            "Character",
            f"Card Person {index} keeps the {LORE_WORDS[index % len(LORE_WORDS)]}.",
        )
        for index in range(CARD_COUNT)
    ]


async def test_embed_documents_and_query_return_768_dims() -> None:
    client = _live_client(_live_settings())

    documents = await client.embed_documents(SAMPLE_TEXTS)
    query = await client.embed_query(QUERY_TEXT)

    assert len(documents) == len(SAMPLE_TEXTS)
    assert all(len(vector) == LIVE_DIM for vector in [*documents, query])
    assert all(isinstance(value, float) for value in query)
    assert _vectors_are_distinct([*documents, query])


async def test_small_master_template_and_playthrough_indexed(
    pool: AsyncConnectionPool, connection: AsyncConnection
) -> None:
    settings = _live_settings()
    service = IndexingService(pool, settings, _live_client(settings))
    playthrough_id = await _build_small_playthrough(connection)

    sweeps, targets, _characters = await _run_sweeps(service)

    total = await _assert_fully_embedded(connection)
    assert targets == total
    active = await connection.execute(SELECT_ACTIVE_MODEL_SQL)
    assert await active.fetchall() == [(LIVE_MODEL_NAME, LIVE_MODEL_VERSION, LIVE_DIM)]
    cursor = await connection.execute(SELECT_INDEXED_SEQ_SQL, (playthrough_id,))
    ingested_seq, indexed_seq = (await cursor.fetchone()) or (None, None)
    assert indexed_seq == ingested_seq == SMALL_TURN_COUNT
    print(f"\nlive small: {total} targets in {sweeps} sweep(s)")


async def test_large_newbie_template_indexed(
    pool: AsyncConnectionPool, connection: AsyncConnection
) -> None:
    settings = _live_settings()
    service = IndexingService(pool, settings, _live_client(settings))
    request = build_newbie_request(_build_cards(), world_lore=_build_lore())
    await TemplateService(connection).build_template(request)
    await connection.commit()

    started = time.perf_counter()
    sweeps, targets, characters = await _run_sweeps(service)
    elapsed = time.perf_counter() - started

    total = await _assert_fully_embedded(connection)
    assert targets == total
    print(
        f"\nlive large newbie: elapsed={elapsed:.1f}s sweeps={sweeps} "
        f"targets={total} targets_per_second={total / elapsed:.1f} "
        f"characters={characters}"
    )
