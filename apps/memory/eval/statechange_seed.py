"""Writes one state-change case into a scratch database: template, entities, ingested
turns and the prior facts the batch may replace."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.models.facts import AliasCreate, EntityCreate, FactCreate
from app.models.ingest import (
    AcceptedDelta,
    FlushItem,
    IngestRequest,
    PlayerEntityPayload,
    RegisterItem,
    RegisterPayload,
    RejectedCall,
    TurnItem,
    TurnPayload,
)
from app.models.templates import TemplateCreate
from app.repositories import entity_repo, fact_repo, template_repo
from app.services.ingest_service import IngestService
from psycopg import AsyncConnection

from eval.statechange_cases import CaseTurn, StateChangeCase

PUBLISH_REVISION = 1
PLAYER_NAME = "The Wanderer"
PRIOR_PROVENANCE = "extracted"
REJECTED_TOOL = "set_state"
FILLER_PREDICATE = "notes_detail"


@dataclass(frozen=True)
class SeededCase:
    playthrough_id: UUID
    entity_ids: dict[str, UUID]
    fact_ids: dict[str, UUID]


def _alias_rows(
    entity_id: UUID, template_id: UUID, names: list[str]
) -> list[AliasCreate]:
    return [
        AliasCreate(
            entity_id=entity_id,
            scope_kind="template",
            scope_id=template_id,
            alias=alias,
            alias_normalized=entity_repo.normalize_alias(alias),
        )
        for alias in dict.fromkeys(names)
    ]


async def _create_entity(
    connection: AsyncConnection,
    template_id: UUID,
    name: str,
    aliases: list[str],
    *,
    is_player: bool,
) -> tuple[UUID, UUID]:
    authored_id = uuid4()
    entity = await entity_repo.create_entity(
        connection,
        EntityCreate(
            scope_kind="template",
            scope_id=template_id,
            authored_entity_id=authored_id,
            entity_type="character",
            canonical_name=name,
            provenance="authored",
            first_seen_seq=0,
            is_player=is_player,
        ),
    )
    rows = _alias_rows(entity.entity_id, template_id, [name, *aliases])
    await entity_repo.add_aliases(connection, rows)
    return authored_id, entity.entity_id


def _turn_item(
    sequence: int, turn: CaseTurn, authored_ids: dict[str, UUID]
) -> TurnItem:
    rejected = [
        RejectedCall(
            tool_name=REJECTED_TOOL,
            arguments={
                "path": f"{authored_ids[item.entity]}.{item.attribute}",
                "value": item.value,
            },
        )
        for item in turn.rejected
    ]
    return TurnItem(
        item_kind="turn",
        sequence=sequence,
        payload=TurnPayload(
            turn_id=uuid4(),
            turn_number=sequence,
            participant_id=uuid4(),
            action_mode="do",
            action_text=turn.action,
            narration_text=turn.narration,
            accepted_delta=AcceptedDelta(items=[]),
            rejected_calls=rejected,
        ),
    )


def _fact_row(
    playthrough_id: UUID, subject: UUID, predicate: str, literal: str
) -> FactCreate:
    return FactCreate(
        scope_kind="playthrough",
        scope_id=playthrough_id,
        subject_entity_id=subject,
        predicate=predicate,
        object_literal=literal,
        authority=PRIOR_PROVENANCE,
        assertion="occurred",
        valid_from_seq=0,
    )


async def _seed_prior_facts(
    connection: AsyncConnection,
    case: StateChangeCase,
    playthrough_id: UUID,
    entity_ids: dict[str, UUID],
) -> dict[str, UUID]:
    rows = [
        _fact_row(
            playthrough_id,
            entity_ids[fact.subject],
            fact.predicate,
            fact.object_literal,
        )
        for fact in case.prior_facts
    ]
    created = await fact_repo.create_facts(connection, rows)
    return {
        fact.key: row.fact_id
        for fact, row in zip(case.prior_facts, created, strict=True)
    }


async def _seed_filler(
    connection: AsyncConnection,
    case: StateChangeCase,
    playthrough_id: UUID,
    entity_ids: dict[str, UUID],
) -> None:
    if case.filler_subject is None or case.filler_count <= 0:
        return
    subject = entity_ids[case.filler_subject]
    rows = [
        _fact_row(
            playthrough_id,
            subject,
            FILLER_PREDICATE,
            f"minor detail number {number} noted during an earlier scene",
        )
        for number in range(case.filler_count)
    ]
    await fact_repo.create_facts(connection, rows)


async def _create_world(
    connection: AsyncConnection, case: StateChangeCase
) -> tuple[UUID, UUID, dict[str, UUID], dict[str, UUID]]:
    scenario_id = uuid4()
    template = await template_repo.create_template(
        connection,
        TemplateCreate(
            scenario_id=scenario_id,
            publish_revision=PUBLISH_REVISION,
            mode="master",
            direct_status="ready",
            enrichment_status="not_needed",
            content_hash=case.case_id,
        ),
    )
    player_authored, _ = await _create_entity(
        connection, template.template_id, PLAYER_NAME, [], is_player=True
    )
    authored_ids: dict[str, UUID] = {}
    entity_ids: dict[str, UUID] = {}
    for entity in case.entities:
        authored, memory_id = await _create_entity(
            connection,
            template.template_id,
            entity.name,
            entity.aliases,
            is_player=False,
        )
        authored_ids[entity.key], entity_ids[entity.key] = authored, memory_id
    return scenario_id, player_authored, authored_ids, entity_ids


def _register_item(scenario_id: UUID, player_authored: UUID) -> RegisterItem:
    return RegisterItem(
        item_kind="register_playthrough",
        sequence=0,
        payload=RegisterPayload(
            scenario_id=scenario_id,
            publish_revision=PUBLISH_REVISION,
            player_entity=PlayerEntityPayload(
                authored_entity_id=player_authored,
                canonical_name=PLAYER_NAME,
                aliases=[],
                entity_type="character",
            ),
            setup_facts=[],
        ),
    )


async def seed_case(connection: AsyncConnection, case: StateChangeCase) -> SeededCase:
    scenario_id, player_authored, authored_ids, entity_ids = await _create_world(
        connection, case
    )
    playthrough_id = uuid4()
    turns = [
        _turn_item(number, turn, authored_ids)
        for number, turn in enumerate(case.turns, start=1)
    ]
    items = [
        _register_item(scenario_id, player_authored),
        *turns,
        FlushItem(item_kind="flush", sequence=len(turns)),
    ]
    await IngestService(connection).ingest_items(
        IngestRequest(playthrough_id=playthrough_id, items=items)
    )
    fact_ids = await _seed_prior_facts(connection, case, playthrough_id, entity_ids)
    await _seed_filler(connection, case, playthrough_id, entity_ids)
    await connection.commit()
    return SeededCase(playthrough_id, entity_ids, fact_ids)
