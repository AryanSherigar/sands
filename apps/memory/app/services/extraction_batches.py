"""Creates due extraction batches and selects the ones ready to run."""

from uuid import UUID

from app.config import Settings
from app.models.jobs import ExtractionBatchCreate, ExtractionBatchRow
from app.models.templates import PlaythroughRow
from app.repositories import extraction_batch_repo, playthrough_repo
from app.services.ingest_common import sha256_hex
from psycopg import AsyncConnection

SECONDS_PER_MINUTE = 60


def batch_window(playthrough: PlaythroughRow, batch_turns: int) -> tuple[int, int]:
    from_seq = playthrough.extracted_seq + 1
    to_seq = min(playthrough.ingested_seq, playthrough.extracted_seq + batch_turns)
    return from_seq, to_seq


def _placeholder_hash(scope_id: UUID, from_seq: int, to_seq: int) -> str:
    return sha256_hex(f"{scope_id}:{from_seq}:{to_seq}:unbuilt")


def _playthrough_batch(
    playthrough: PlaythroughRow, settings: Settings
) -> ExtractionBatchCreate:
    from_seq, to_seq = batch_window(playthrough, settings.extraction_batch_turns)
    return ExtractionBatchCreate(
        scope_kind="playthrough",
        scope_id=playthrough.playthrough_id,
        from_seq=from_seq,
        to_seq=to_seq,
        status="pending",
        model=settings.extraction_model_name,
        prompt_version=settings.extraction_prompt_version,
        input_hash=_placeholder_hash(playthrough.playthrough_id, from_seq, to_seq),
    )


async def create_due_playthrough_batches(
    connection: AsyncConnection, settings: Settings, playthrough_id: UUID | None
) -> int:
    due = await playthrough_repo.list_playthroughs_due_for_extraction(
        connection, settings.extraction_batch_turns, playthrough_id
    )
    for playthrough in due:
        await extraction_batch_repo.create_batch(
            connection, _playthrough_batch(playthrough, settings)
        )
    return len(due)


def backoff_delay_seconds(settings: Settings) -> list[int]:
    return [
        minutes * SECONDS_PER_MINUTE for minutes in settings.extraction_backoff_minutes
    ]


async def list_ready_batches(
    connection: AsyncConnection, settings: Settings, scope_id: UUID | None
) -> list[ExtractionBatchRow]:
    return await extraction_batch_repo.list_due_pending_batches(
        connection, backoff_delay_seconds(settings), scope_id
    )
