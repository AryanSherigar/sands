"""Turns an accepted `<entity_uuid>.<attr>` state mutation into an accepted fact
that supersedes the value it replaces."""

from uuid import UUID

from app.models.evidence import EventRow
from app.models.facts import FactCreate, FactRow, SupersessionCreate
from app.models.ingest import AcceptedDeltaItem
from app.repositories import entity_repo, fact_repo
from app.services.accepted_fact_mapper import (
    canonical_value,
    is_noop_value,
    parse_entity_attribute_path,
)
from app.services.ingest_common import (
    PLAYTHROUGH_SCOPE,
    TEMPLATE_SCOPE,
    TurnContext,
    memory_scopes,
)


async def apply_accepted_mutation(
    context: TurnContext, event: EventRow, item: AcceptedDeltaItem
) -> None:
    parsed = parse_entity_attribute_path(item.key)
    if parsed is None:
        return
    authored_entity_id, attribute = parsed
    entity_id = await _resolve_entity_id(context, authored_entity_id)
    if entity_id is None:
        return
    literal = canonical_value(item.after)
    current = await fact_repo.list_valid_facts_at(
        context.connection,
        context.playthrough_id,
        context.template_id,
        event.sequence,
        subject_entity_ids=[entity_id],
        predicate=attribute,
    )
    if is_noop_value([fact.object_literal for fact in current], literal):
        return
    new_fact = await _create_accepted_fact(
        context, event, entity_id, attribute, literal
    )
    await _supersede_current(context, event, current, new_fact)
    await _supersede_if_late(context, new_fact)


async def _resolve_entity_id(
    context: TurnContext, authored_entity_id: UUID
) -> UUID | None:
    rows = await entity_repo.get_entities_by_authored_ids(
        context.connection,
        memory_scopes(context.playthrough_id, context.template_id),
        [authored_entity_id],
    )
    if not rows:
        return None
    template_rows = [row for row in rows if row.scope_kind == TEMPLATE_SCOPE]
    return (template_rows or rows)[0].entity_id


async def _create_accepted_fact(
    context: TurnContext,
    event: EventRow,
    entity_id: UUID,
    attribute: str,
    literal: str,
) -> FactRow:
    fact = FactCreate(
        scope_kind=PLAYTHROUGH_SCOPE,
        scope_id=context.playthrough_id,
        subject_entity_id=entity_id,
        predicate=attribute,
        object_literal=literal,
        authority="accepted",
        assertion="occurred",
        valid_from_seq=event.sequence,
        event_id=event.event_id,
    )
    rows = await fact_repo.create_facts(context.connection, [fact])
    return rows[0]


async def _supersede_current(
    context: TurnContext,
    event: EventRow,
    current: list[FactRow],
    new_fact: FactRow,
) -> None:
    rows = [
        SupersessionCreate(
            playthrough_id=context.playthrough_id,
            fact_id=fact.fact_id,
            at_seq=event.sequence,
            superseding_fact_id=new_fact.fact_id,
            authority="accepted",
            event_id=event.event_id,
        )
        for fact in current
    ]
    await fact_repo.add_supersessions(context.connection, rows)


async def _supersede_if_late(context: TurnContext, new_fact: FactRow) -> None:
    # NOTE: the prior value was already superseded at the later sequence; the new
    # fact must also end there, or two values would be valid from then on.
    later = await fact_repo.list_accepted_facts_after(
        context.connection,
        context.playthrough_id,
        new_fact.subject_entity_id,
        new_fact.predicate,
        new_fact.valid_from_seq,
    )
    if not later:
        return
    earliest = later[0]
    supersession = SupersessionCreate(
        playthrough_id=context.playthrough_id,
        fact_id=new_fact.fact_id,
        at_seq=earliest.valid_from_seq,
        superseding_fact_id=earliest.fact_id,
        authority="accepted",
        event_id=earliest.event_id,
    )
    await fact_repo.add_supersessions(context.connection, [supersession])
