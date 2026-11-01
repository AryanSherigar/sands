"""Measure indexing sweep latency on the test database.

Usage:
    python -m scripts.measure_indexing_latency     (from apps/memory/)
    python scripts/measure_indexing_latency.py [--live] [--fake-latency-ms N]

Measures IndexingService.process_pending sweep latency:
1. "12-turn burst": ingest 12 turns, run ONE sweep, report elapsed and indexed_seq.
2. "template N targets": ~1,500 span template, sweeps until completion.

Optional --live: use real Google Vertex AI embedding client (requires GOOGLE_CLOUD_API_KEY).
Optional --fake-latency-ms: add delay per fake embed call to simulate network latency.
"""

import argparse
import asyncio
import hashlib
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

from app.config import Settings, get_settings
from app.db.migrate import apply_migrations
from app.integrations.embedding_client import build_embedding_client
from app.models.ingest import (
    AcceptedDelta,
    AcceptedDeltaItem,
    IngestRequest,
    RegisterItem,
    RegisterPayload,
    RejectedCall,
    TurnItem,
    TurnPayload,
)
from app.models.templates import (
    NewbieTemplateContent,
    StoryCardPayload,
    TemplateBuildRequest,
)
from app.services.indexing_service import IndexingService
from app.services.ingest_service import IngestService
from app.services.template_service import TemplateService
from psycopg import AsyncConnection, sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import AsyncConnectionPool

TEST_DIM = 8
DROP_DATABASE = "DROP DATABASE IF EXISTS {database} WITH (FORCE)"
CREATE_DATABASE = "CREATE DATABASE {database}"
LORE_WORDS = [
    "The",
    "river",
    "changed",
    "course",
    "long",
    "before",
    "the",
    "ferrymen",
    "learned",
    "to",
    "read",
    "its",
    "moods",
    "and",
    "the",
    "villages",
    "along",
    "its",
    "bank",
    "forgot",
    "the",
    "older",
    "names",
]
LORE_WORD_COUNT = 300_000
WORDS_PER_PARAGRAPH = 100
CARD_COUNT = 50
NARRATION_WORDS = [
    "The",
    "brave",
    "adventurer",
    "stood",
    "at",
    "the",
    "crossroads,",
    "facing",
    "a",
    "moment",
]
TURN_COUNT = 12
ACTION_TEXT = "The hero readies their weapon."
REJECTED_TOOL_NAME = "cast_spell"


def vector_for(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [(byte + 1) / 256 for byte in digest[:TEST_DIM]]


class FakeEmbedder:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        self._delay_seconds = delay_seconds

    async def embed_documents(
        self, texts: list[str], deadline_monotonic: float | None = None
    ) -> list[list[float]]:
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)
        return [vector_for(text) for text in texts]


def _lore_text() -> str:
    paragraph_count = LORE_WORD_COUNT // WORDS_PER_PARAGRAPH
    paragraph = " ".join(
        LORE_WORDS[i % len(LORE_WORDS)] for i in range(WORDS_PER_PARAGRAPH)
    )
    return "\n\n".join(paragraph for _ in range(paragraph_count))


def _newbie_template() -> TemplateBuildRequest:
    cards = [
        StoryCardPayload(
            card_id=f"card-{i}",
            type="Character",
            name=f"Card Person {i}",
            content=f"Card Person {i} lives beside the river.",
        )
        for i in range(CARD_COUNT)
    ]
    return TemplateBuildRequest(
        scenario_id=uuid4(),
        publish_revision=1,
        mode="newbie",
        content_hash="measure",
        newbie=NewbieTemplateContent(story_cards=cards, world_lore=_lore_text()),
    )


def _build_turn_payload(sequence: int) -> TurnPayload:
    return TurnPayload(
        turn_id=uuid4(),
        turn_number=sequence,
        participant_id=uuid4(),
        action_mode="do",
        action_text=ACTION_TEXT,
        narration_text=" ".join(NARRATION_WORDS),
        accepted_delta=AcceptedDelta(
            items=[AcceptedDeltaItem(kind="state_mutation", key="hp", after=100)]
        ),
        rejected_calls=[
            RejectedCall(
                tool_name=REJECTED_TOOL_NAME,
                arguments={"spell": "fireball"},
                result={"error": "insufficient_mana"},
            )
        ],
    )


async def _create_template(connection: AsyncConnection) -> UUID:
    from app.models.templates import TemplateCreate
    from app.repositories import template_repo

    scenario_id = uuid4()
    await template_repo.create_template(
        connection,
        TemplateCreate(
            scenario_id=scenario_id,
            publish_revision=1,
            mode="master",
            direct_status="ready",
            enrichment_status="not_needed",
            content_hash="hash",
        ),
    )
    return scenario_id


async def _register_and_ingest_turns(
    connection: AsyncConnection,
    playthrough_id: UUID,
    turn_count: int,
) -> None:
    service = IngestService(connection)
    scenario_id = await _create_template(connection)
    register_item = RegisterItem(
        item_kind="register_playthrough",
        sequence=0,
        payload=RegisterPayload(
            scenario_id=scenario_id,
            publish_revision=1,
            player_entity=None,
            setup_facts=[],
        ),
    )
    await service.ingest_items(
        IngestRequest(playthrough_id=playthrough_id, items=[register_item])
    )
    for seq in range(1, turn_count + 1):
        turn_item = TurnItem(
            item_kind="turn", sequence=seq, payload=_build_turn_payload(seq)
        )
        await service.ingest_items(
            IngestRequest(playthrough_id=playthrough_id, items=[turn_item])
        )


async def _read_indexed_seq(connection: AsyncConnection, playthrough_id: UUID) -> int:
    cursor = await connection.execute(
        "SELECT indexed_seq FROM memory_playthrough WHERE playthrough_id = %s",
        (playthrough_id,),
    )
    row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def _measure_burst(
    pool: AsyncConnectionPool,
    settings: Settings,
    embedder: FakeEmbedder,
) -> None:
    playthrough_id = uuid4()
    async with pool.connection() as conn:
        await _register_and_ingest_turns(conn, playthrough_id, TURN_COUNT)
        await conn.commit()

    start = time.perf_counter()
    service = IndexingService(pool, settings, embedder)
    await service.process_pending()
    elapsed = time.perf_counter() - start

    async with pool.connection() as conn:
        indexed_seq = await _read_indexed_seq(conn, playthrough_id)
        status = "PASS" if indexed_seq == TURN_COUNT else "FAIL"
        print(f"12-turn burst: {elapsed:.2f}s indexed_seq={indexed_seq} {status}")
        await conn.rollback()


async def _measure_template_sweeps(
    pool: AsyncConnectionPool,
    settings: Settings,
    embedder: FakeEmbedder,
) -> None:
    async with pool.connection() as conn:
        await TemplateService(conn).build_template(_newbie_template())
        await conn.commit()

    sweep_count = 0
    total_elapsed = 0.0
    total_targets = 0
    while True:
        sweep_start = time.perf_counter()
        service = IndexingService(pool, settings, embedder)
        response = await service.process_pending()
        sweep_elapsed = time.perf_counter() - sweep_start
        total_elapsed += sweep_elapsed
        sweep_count += 1
        targets = response.counts.spans_embedded + response.counts.facts_embedded
        total_targets += targets
        if response.embedding_step == "completed":
            break

    tps = total_targets / total_elapsed if total_elapsed > 0 else 0
    print(
        f"template N targets: {sweep_count} sweeps, {total_elapsed:.2f}s total, "
        f"{tps:.0f} targets/sec"
    )


ENV_FILE_PATH = Path(__file__).resolve().parents[3] / ".env"
API_KEY_LINE_PREFIX = "GOOGLE_CLOUD_API_KEY="
FAKE_MODEL_NAME = "latency-fake-model"
LIVE_DIM = 768
SCRATCH_DATABASE_NAME = "memory_indexing_latency_db"
MAINTENANCE_DATABASE_NAME = "postgres"


def _read_api_key_from_env() -> str:
    if not ENV_FILE_PATH.exists():
        return ""
    for line in ENV_FILE_PATH.read_text().splitlines():
        if line.startswith(API_KEY_LINE_PREFIX):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def _build_settings(args: argparse.Namespace, api_key: str) -> Settings:
    if args.live:
        return Settings(embedding_api_key=api_key, embedding_dim=LIVE_DIM)
    return Settings(
        embedding_model_name=FAKE_MODEL_NAME, embedding_dim=args.dim or TEST_DIM
    )


async def _run_on_scratch_database(base_url: str, name: str, action: str) -> None:
    maintenance_url = make_conninfo(base_url, dbname=MAINTENANCE_DATABASE_NAME)
    statement = sql.SQL(action).format(database=sql.Identifier(name))
    async with await AsyncConnection.connect(
        maintenance_url, autocommit=True
    ) as connection:
        await connection.execute(statement)


async def main(args: argparse.Namespace) -> None:
    api_key = _read_api_key_from_env() if args.live else ""
    if args.live and not api_key:
        print("Error: --live requires GOOGLE_CLOUD_API_KEY in .env", file=sys.stderr)
        sys.exit(1)
    settings = _build_settings(args, api_key)
    fake_latency_seconds = (args.fake_latency_ms or 0) / 1000.0
    embedder = (
        build_embedding_client(settings)
        if args.live
        else FakeEmbedder(delay_seconds=fake_latency_seconds)
    )

    base_url = get_settings().memory_test_database_url
    scratch_url = make_conninfo(base_url, dbname=SCRATCH_DATABASE_NAME)
    await _run_on_scratch_database(base_url, SCRATCH_DATABASE_NAME, DROP_DATABASE)
    await _run_on_scratch_database(base_url, SCRATCH_DATABASE_NAME, CREATE_DATABASE)
    try:
        await apply_migrations(scratch_url)
        pool = AsyncConnectionPool(
            conninfo=scratch_url, min_size=1, max_size=5, open=False
        )
        await pool.open()
        try:
            await _measure_burst(pool, settings, embedder)
            await _measure_template_sweeps(pool, settings, embedder)
        finally:
            await pool.close()
    finally:
        await _run_on_scratch_database(base_url, SCRATCH_DATABASE_NAME, DROP_DATABASE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure indexing service latency")
    parser.add_argument("--live", action="store_true", help="Use real Vertex AI client")
    parser.add_argument(
        "--fake-latency-ms", type=int, help="Add latency to fake embedder"
    )
    parser.add_argument("--dim", type=int, help="Override embedding dimension")
    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
