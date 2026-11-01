"""Reasons a retrieval answer may be incomplete. Reported, never raised."""

from app.models.retrieve import DegradedReason
from app.models.templates import PlaythroughRow
from app.repositories import extraction_batch_repo, template_repo
from psycopg import AsyncConnection


def is_indexing_lagging(playthrough: PlaythroughRow, recent_window_turns: int) -> bool:
    lag = playthrough.latest_seq_seen - playthrough.indexed_seq
    return lag > recent_window_turns


async def _is_template_missing(
    connection: AsyncConnection, playthrough: PlaythroughRow
) -> bool:
    if playthrough.template_id is None:
        return True
    template = await template_repo.get_template(connection, playthrough.template_id)
    return template is None


async def compute_degraded_reasons(
    connection: AsyncConnection,
    playthrough: PlaythroughRow,
    *,
    recent_window_turns: int,
) -> list[DegradedReason]:
    """In fixed order: extraction_failed, indexing_lag, template_missing."""
    reasons: list[DegradedReason] = []
    has_failed_batch = await extraction_batch_repo.has_failed_batch(
        connection, "playthrough", playthrough.playthrough_id
    )
    if has_failed_batch:
        reasons.append("extraction_failed")
    if is_indexing_lagging(playthrough, recent_window_turns):
        reasons.append("indexing_lag")
    if await _is_template_missing(connection, playthrough):
        reasons.append("template_missing")
    return reasons
