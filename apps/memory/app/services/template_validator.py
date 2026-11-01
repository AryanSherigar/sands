"""Pure validation of a template build request. Reasons carry ids and field names only."""

from collections.abc import Iterable
from typing import TypeVar
from uuid import UUID

from app.exceptions.template_exceptions import TemplateValidationError
from app.models.templates import (
    MasterTemplateContent,
    NewbieTemplateContent,
    TemplateBuildRequest,
    TemplateConnectionPayload,
    TemplateEntityPayload,
    TemplateFactPayload,
)

MAX_PLAYER_ENTITIES = 1
IdType = TypeVar("IdType", UUID, str)


def validate_template_request(request: TemplateBuildRequest) -> None:
    _require_matching_content(request)
    if request.master is not None:
        _validate_master(request.master)
    if request.newbie is not None:
        _validate_newbie(request.newbie)


def _require_matching_content(request: TemplateBuildRequest) -> None:
    has_master = request.master is not None
    has_newbie = request.newbie is not None
    is_master_mode = request.mode == "master"
    if has_master != is_master_mode or has_newbie == is_master_mode:
        raise TemplateValidationError(f"content does not match mode {request.mode}")


def _validate_master(content: MasterTemplateContent) -> None:
    entity_ids = _validate_authored_graph(content.entities, content.facts)
    fact_ids = {fact.fact_id for fact in content.facts}
    connection_ids = _unique_ids(
        "connection_id", [item.connection_id for item in content.map_connections]
    )
    _require_disjoint_authored_ids(fact_ids, connection_ids)
    for connection in content.map_connections:
        _validate_connection(connection, entity_ids)


def _validate_newbie(content: NewbieTemplateContent) -> None:
    _unique_ids("card_id", [card.card_id for card in content.story_cards])
    _validate_authored_graph(content.entities, content.facts)


def _validate_authored_graph(
    entities: list[TemplateEntityPayload], facts: list[TemplateFactPayload]
) -> set[UUID]:
    entity_ids = _unique_ids("entity_id", [item.entity_id for item in entities])
    fact_ids = _unique_ids("fact_id", [item.fact_id for item in facts])
    _require_single_player(entities)
    for fact in facts:
        _validate_fact(fact, entity_ids, fact_ids)
    _validate_supersession_chains(facts)
    return entity_ids


def _unique_ids(label: str, ids: Iterable[IdType]) -> set[IdType]:
    seen: set[IdType] = set()
    for item in ids:
        if item in seen:
            raise TemplateValidationError(f"duplicate {label} {item}")
        seen.add(item)
    return seen


def _require_disjoint_authored_ids(
    fact_ids: set[UUID], connection_ids: set[UUID]
) -> None:
    shared = fact_ids & connection_ids
    if shared:
        raise TemplateValidationError(f"fact and connection share id {min(shared)}")


def _require_single_player(entities: list[TemplateEntityPayload]) -> None:
    player_count = sum(1 for entity in entities if entity.is_player)
    if player_count > MAX_PLAYER_ENTITIES:
        raise TemplateValidationError("more than one player entity")


def _validate_fact(
    fact: TemplateFactPayload, entity_ids: set[UUID], fact_ids: set[UUID]
) -> None:
    has_object_entity = fact.object_entity_id is not None
    has_object_literal = fact.object_literal is not None
    if has_object_entity == has_object_literal:
        raise TemplateValidationError(f"fact {fact.fact_id} needs exactly one object")
    _require_known_entity(fact.subject_entity_id, entity_ids, fact.fact_id)
    if fact.object_entity_id is not None:
        _require_known_entity(fact.object_entity_id, entity_ids, fact.fact_id)
    if fact.superseded_fact_id is not None and fact.superseded_fact_id not in fact_ids:
        raise TemplateValidationError(f"fact {fact.fact_id} supersedes unknown fact")


def _validate_connection(
    connection: TemplateConnectionPayload, entity_ids: set[UUID]
) -> None:
    for endpoint in (connection.entity_id_a, connection.entity_id_b):
        _require_known_entity(endpoint, entity_ids, connection.connection_id)


def _require_known_entity(
    entity_id: UUID, entity_ids: set[UUID], owner_id: UUID
) -> None:
    if entity_id not in entity_ids:
        raise TemplateValidationError(
            f"{owner_id} references unknown entity {entity_id}"
        )


def _validate_supersession_chains(facts: list[TemplateFactPayload]) -> None:
    links = {
        fact.fact_id: fact.superseded_fact_id
        for fact in facts
        if fact.superseded_fact_id is not None
    }
    for start in links:
        _require_chain_terminates(start, links)


def _require_chain_terminates(start: UUID, links: dict[UUID, UUID | None]) -> None:
    seen = {start}
    current = links.get(start)
    while current is not None:
        if current in seen:
            raise TemplateValidationError(f"supersession cycle at fact {start}")
        seen.add(current)
        current = links.get(current)
