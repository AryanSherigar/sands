"""Applies a participants item: merges names into the registered playthrough."""

from uuid import UUID

from app.exceptions.ingest_exceptions import PlaythroughNotRegisteredError
from app.models.ingest import ParticipantsPayload
from app.models.templates import ParticipantPayload
from app.repositories import playthrough_repo
from app.services.ingest_common import OUTCOME_APPLIED, OUTCOME_DUPLICATE, ItemOutcome
from psycopg import AsyncConnection


def merge_participants(
    existing: list[ParticipantPayload], incoming: list[ParticipantPayload]
) -> list[ParticipantPayload]:
    """Adds new participants and refreshes names; never removes anyone."""
    merged = {item.participant_id: item for item in existing}
    merged.update({item.participant_id: item for item in incoming})
    return list(merged.values())


async def apply_participants_item(
    connection: AsyncConnection, playthrough_id: UUID, payload: ParticipantsPayload
) -> ItemOutcome:
    existing = await playthrough_repo.get_participants_for_update(
        connection, playthrough_id
    )
    if existing is None:
        raise PlaythroughNotRegisteredError(playthrough_id)
    merged = merge_participants(existing, payload.participants)
    if merged == existing:
        return OUTCOME_DUPLICATE
    await playthrough_repo.set_participants(connection, playthrough_id, merged)
    return OUTCOME_APPLIED
