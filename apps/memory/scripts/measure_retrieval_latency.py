"""Measure end-to-end RetrievalService.retrieve latency on scratch databases.

Usage:
    .venv/bin/python -m scripts.measure_retrieval_latency     (from apps/memory/)

Each corpus is built in its own freshly migrated scratch database (dropped
afterwards), embedded by the real IndexingService with deterministic 768-dim hash
vectors, then queried by the real RetrievalService with a zero-latency hash query
embedder. Any retrieve exception, skipped branch or service warning aborts the run.
The 150 ms p95 target is reported, never enforced.
"""

import asyncio
import random
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config import Settings, get_settings
from app.db.migrate import apply_migrations
from app.services.retrieval_service import RetrievalService
from psycopg import AsyncConnection, sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import AsyncConnectionPool

from scripts import retrieval_latency_report as report
from scripts import retrieval_latency_stats as stats
from scripts.retrieval_latency_build import build_corpus
from scripts.retrieval_latency_index import index_corpus, read_counts, verify_counts
from scripts.retrieval_latency_queries import load_query_pools
from scripts.retrieval_latency_run import build_requests, run_queries
from scripts.retrieval_latency_types import BuiltCorpus, CorpusSpec
from scripts.retrieval_latency_vectors import EMBEDDING_DIM, embed_query

SEED = 20261026
QUERY_COUNT = 200
WARMUP_COUNT = 10
SCRATCH_DATABASE_NAME = "memory_retrieval_latency_db"
MAINTENANCE_DATABASE_NAME = "postgres"
DROP_DATABASE = "DROP DATABASE IF EXISTS {database} WITH (FORCE)"
CREATE_DATABASE = "CREATE DATABASE {database}"
ANALYZE_STATEMENT = "ANALYZE"
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 8
FAKE_MODEL_NAME = "latency-fake-model"
FAKE_API_KEY = "latency-fake-key"
CORPUS_SPECS = [
    CorpusSpec(
        name="burst",
        mode="master",
        entity_count=15,
        relation_fact_count=20,
        attribute_fact_count=10,
        hub_count=0,
        turn_count=12,
        hidden_fraction=0.0,
        commitment_count=3,
        scene_every_turns=0,
        target_embeddable=None,
        fixed_lore_count=10,
    ),
    CorpusSpec(
        name="newbie-3k",
        mode="newbie",
        entity_count=50,
        relation_fact_count=100,
        attribute_fact_count=100,
        hub_count=0,
        turn_count=30,
        hidden_fraction=0.2,
        commitment_count=6,
        scene_every_turns=0,
        target_embeddable=3000,
        fixed_lore_count=0,
    ),
    CorpusSpec(
        name="novel-10k",
        mode="master",
        entity_count=300,
        relation_fact_count=1000,
        attribute_fact_count=500,
        hub_count=5,
        turn_count=100,
        hidden_fraction=0.2,
        commitment_count=30,
        scene_every_turns=25,
        target_embeddable=10000,
        fixed_lore_count=0,
    ),
]


async def _run_on_maintenance(base_url: str, statement: str) -> None:
    maintenance_url = make_conninfo(base_url, dbname=MAINTENANCE_DATABASE_NAME)
    query = sql.SQL(statement).format(database=sql.Identifier(SCRATCH_DATABASE_NAME))
    async with await AsyncConnection.connect(
        maintenance_url, autocommit=True
    ) as connection:
        await connection.execute(query)


@asynccontextmanager
async def scratch_database(base_url: str) -> AsyncIterator[str]:
    await _run_on_maintenance(base_url, DROP_DATABASE)
    await _run_on_maintenance(base_url, CREATE_DATABASE)
    try:
        scratch_url = make_conninfo(base_url, dbname=SCRATCH_DATABASE_NAME)
        await apply_migrations(scratch_url)
        yield scratch_url
    finally:
        await _run_on_maintenance(base_url, DROP_DATABASE)


def build_settings() -> Settings:
    return Settings(
        embedding_api_key=FAKE_API_KEY,
        embedding_model_name=FAKE_MODEL_NAME,
        embedding_dim=EMBEDDING_DIM,
    )


async def analyze_database(scratch_url: str) -> None:
    async with await AsyncConnection.connect(
        scratch_url, autocommit=True
    ) as connection:
        await connection.execute(ANALYZE_STATEMENT)


async def build_and_index(
    scratch_url: str, pool: AsyncConnectionPool, spec: CorpusSpec, settings: Settings
) -> BuiltCorpus:
    rng = random.Random(f"{SEED}:{spec.name}")
    started = time.perf_counter()
    async with await AsyncConnection.connect(scratch_url) as connection:
        corpus = await build_corpus(connection, spec, rng)
    build_seconds = time.perf_counter() - started
    index = await index_corpus(pool, settings)
    await analyze_database(scratch_url)
    async with pool.connection() as connection:
        counts = await read_counts(connection, corpus)
    deviation = verify_counts(corpus, counts)
    report.print_counts(corpus, counts, deviation, (build_seconds, index))
    corpus.turn_count = counts.ingested_turns
    return corpus


async def measure_corpus(base_url: str, spec: CorpusSpec) -> report.CorpusReport:
    settings = build_settings()
    async with scratch_database(base_url) as scratch_url:
        pool = AsyncConnectionPool(
            conninfo=scratch_url,
            min_size=POOL_MIN_SIZE,
            max_size=POOL_MAX_SIZE,
            open=False,
        )
        await pool.open()
        try:
            corpus = await build_and_index(scratch_url, pool, spec, settings)
            return await run_corpus_queries(pool, settings, corpus)
        finally:
            await pool.close()


async def run_corpus_queries(
    pool: AsyncConnectionPool, settings: Settings, corpus: BuiltCorpus
) -> report.CorpusReport:
    rng = random.Random(f"{SEED}:{corpus.spec.name}:queries")
    async with pool.connection() as connection:
        pools = await load_query_pools(connection, corpus)
    requests = build_requests(
        rng, corpus, pools, corpus.turn_count, WARMUP_COUNT + QUERY_COUNT
    )
    service = RetrievalService(pool, settings, embed_query)
    run = await run_queries(service, requests, WARMUP_COUNT)
    report.print_branch_stats(stats.summarize_branches(run.responses, run.logs), run)
    return report.build_report(corpus.spec.name, run)


async def main() -> None:
    base_url = get_settings().memory_test_database_url
    reports = [await measure_corpus(base_url, spec) for spec in CORPUS_SPECS]
    report.print_latency_table(reports)
    report.print_stage_table(reports)


if __name__ == "__main__":
    asyncio.run(main())
