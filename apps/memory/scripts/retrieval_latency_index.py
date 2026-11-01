"""Embeds a built corpus with the real IndexingService and measures what exists."""

import time
from dataclasses import dataclass

from app.config import Settings
from app.services.indexing_service import IndexingService
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from scripts.retrieval_latency_types import BuiltCorpus, MeasurementError
from scripts.retrieval_latency_vectors import HashDocumentEmbedder

MAX_SWEEPS = 200
HUB_DEGREE_THRESHOLD = 20
SIZE_TOLERANCE = 0.10
IDLE_STEP = "idle"
CONTINUE_STEPS = {"completed", "deadline_reached"}
COUNTS_SQL = """
SELECT
    (SELECT count(*) FROM memory_span) AS spans,
    (SELECT count(*) FROM memory_fact) AS facts,
    (SELECT count(*) FROM memory_embedding AS e
        JOIN memory_embedding_model AS m
            ON m.model = e.model AND m.model_version = e.model_version
        WHERE m.is_active) AS embeddings,
    (SELECT count(*) FROM memory_span WHERE is_hidden)
        + (SELECT count(*) FROM memory_fact WHERE is_hidden) AS hidden,
    (SELECT count(*) FROM memory_span WHERE conditional)
        + (SELECT count(*) FROM memory_fact WHERE conditional) AS conditional,
    (SELECT count(*) FROM memory_entity) AS entities,
    (SELECT count(*) FROM memory_alias) AS aliases,
    (SELECT count(*) FROM memory_fact WHERE object_entity_id IS NOT NULL) AS relations,
    (SELECT count(*) FROM memory_commitment) AS commitments,
    (SELECT count(*) FROM memory_commitment_status) AS commitment_statuses,
    (SELECT ingested_seq FROM memory_playthrough WHERE playthrough_id = %(playthrough_id)s)
        AS ingested_turns,
    (SELECT indexed_seq FROM memory_playthrough WHERE playthrough_id = %(playthrough_id)s)
        AS indexed_turns
"""
DEGREE_SQL = """
SELECT count(*) FILTER (WHERE degree > %(threshold)s) AS hubs,
    coalesce(max(degree), 0) AS max_degree
FROM (
    SELECT entity_id, count(*) AS degree FROM (
        SELECT subject_entity_id AS entity_id FROM memory_fact
        WHERE object_entity_id IS NOT NULL
        UNION ALL
        SELECT object_entity_id FROM memory_fact WHERE object_entity_id IS NOT NULL
    ) AS endpoints GROUP BY entity_id
) AS degrees
"""


@dataclass(frozen=True)
class IndexResult:
    sweeps: int
    seconds: float


@dataclass(frozen=True)
class CorpusCounts:
    spans: int
    facts: int
    embeddings: int
    hidden: int
    conditional: int
    entities: int
    aliases: int
    relations: int
    commitments: int
    commitment_statuses: int
    ingested_turns: int
    indexed_turns: int
    hubs: int
    max_degree: int


async def index_corpus(pool: AsyncConnectionPool, settings: Settings) -> IndexResult:
    service = IndexingService(pool, settings, HashDocumentEmbedder())
    started = time.perf_counter()
    for sweep in range(1, MAX_SWEEPS + 1):
        response = await service.process_pending()
        is_healthy = response.embedding_step in {IDLE_STEP, *CONTINUE_STEPS}
        if response.errors or response.counts.targets_skipped or not is_healthy:
            raise MeasurementError(f"Indexing reported problems: {response}")
        if response.embedding_step == IDLE_STEP:
            return IndexResult(sweep, time.perf_counter() - started)
    raise MeasurementError(f"Indexing did not finish within {MAX_SWEEPS} sweeps.")


async def read_counts(connection: AsyncConnection, corpus: BuiltCorpus) -> CorpusCounts:
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(COUNTS_SQL, {"playthrough_id": corpus.playthrough_id})
        counts = await cursor.fetchone()
        await cursor.execute(DEGREE_SQL, {"threshold": HUB_DEGREE_THRESHOLD})
        degrees = await cursor.fetchone()
    if counts is None or degrees is None:
        raise MeasurementError("Count queries returned no row.")
    return CorpusCounts(**counts, **degrees)


def verify_counts(corpus: BuiltCorpus, counts: CorpusCounts) -> float | None:
    """Returns the deviation from the intended size, or None when none was intended."""
    if counts.embeddings != counts.spans + counts.facts:
        raise MeasurementError(
            f"{corpus.spec.name}: {counts.embeddings} embeddings for "
            f"{counts.spans + counts.facts} spans and facts."
        )
    target = corpus.spec.target_embeddable
    if target is None:
        return None
    deviation = (counts.embeddings - target) / target
    if abs(deviation) > SIZE_TOLERANCE:
        raise MeasurementError(
            f"{corpus.spec.name}: {counts.embeddings} embedded targets is "
            f"{deviation:+.1%} from the intended {target}."
        )
    return deviation
