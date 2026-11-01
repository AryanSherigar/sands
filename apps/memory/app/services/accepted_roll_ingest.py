"""Turns an accepted resolved check into an accepted fact about the player.

Unlike a state mutation, a roll never supersedes anything: earlier checks of the
same type must stay recallable.
"""

from app.models.evidence import EventRow
from app.models.facts import FactCreate
from app.models.ingest import AcceptedDeltaItem
from app.repositories import fact_repo, playthrough_repo
from app.services.accepted_fact_mapper import describe_roll
from app.services.ingest_common import PLAYTHROUGH_SCOPE, TurnContext

ROLL_PREDICATE = "check_result"


async def apply_accepted_roll(
    context: TurnContext, event: EventRow, item: AcceptedDeltaItem
) -> None:
    description = describe_roll(item)
    if description is None:
        return
    playthrough = await playthrough_repo.get_playthrough(
        context.connection, context.playthrough_id
    )
    if playthrough is None or playthrough.player_entity_id is None:
        return
    fact = FactCreate(
        scope_kind=PLAYTHROUGH_SCOPE,
        scope_id=context.playthrough_id,
        subject_entity_id=playthrough.player_entity_id,
        predicate=ROLL_PREDICATE,
        object_literal=description,
        authority="accepted",
        assertion="occurred",
        valid_from_seq=event.sequence,
        event_id=event.event_id,
    )
    await fact_repo.create_facts(context.connection, [fact])
