"""Advances each playthrough's indexed_seq from the spans embedded so far."""

from uuid import UUID

from app.models.jobs import EmbeddingModelRow
from app.models.templates import PlaythroughRow
from app.repositories import playthrough_repo, span_repo
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool


def compute_indexed_seq(ingested_seq: int, first_unembedded_seq: int | None) -> int:
    if first_unembedded_seq is None:
        return ingested_seq
    return min(ingested_seq, first_unembedded_seq - 1)


async def _advance_one(
    connection: AsyncConnection,
    playthrough: PlaythroughRow,
    model: EmbeddingModelRow,
    failure_limit: int,
) -> bool:
    first_unembedded_seq = await span_repo.first_unembedded_sequence(
        connection,
        playthrough.playthrough_id,
        model.model,
        model.model_version,
        failure_limit,
    )
    indexed_seq = compute_indexed_seq(playthrough.ingested_seq, first_unembedded_seq)
    if indexed_seq <= playthrough.indexed_seq:
        return False
    await playthrough_repo.advance_watermarks(
        connection, playthrough.playthrough_id, indexed_seq=indexed_seq
    )
    return True


async def advance_index_watermarks(
    pool: AsyncConnectionPool,
    model: EmbeddingModelRow,
    failure_limit: int,
    playthrough_id: UUID | None,
) -> int:
    advanced = 0
    async with pool.connection() as connection:
        behind = await playthrough_repo.list_playthroughs_behind_index(
            connection, playthrough_id
        )
        for playthrough in behind:
            advanced += await _advance_one(
                connection, playthrough, model, failure_limit
            )
    return advanced
