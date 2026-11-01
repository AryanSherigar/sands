"""Builders for ingest_service integration tests: a seeded template world and
wire-contract items, built through the app's own repositories and models."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.models.facts import AliasCreate, EntityCreate, FactCreate, FactRow
from app.models.ingest import (
    AcceptedDelta,
    AcceptedDeltaItem,
    FlushItem,
    IngestRequest,
    PlayerEntityPayload,
    RegisterItem,
    RegisterPayload,
    RejectedCall,
    SetupFactPayload,
    TurnItem,
    TurnPayload,
)
from app.models.templates import TemplateCreate
from app.repositories import entity_repo, fact_repo, template_repo
from psycopg import AsyncConnection, sql

PUBLISH_REVISION = 3
INITIAL_RANK = "captain"
PLAYER_TEMPLATE_NAME = "The Wanderer"
COUNTED_TABLES = (
    "memory_playthrough",
    "memory_source",
    "memory_span",
    "memory_event",
    "memory_entity",
    "memory_alias",
    "memory_fact",
    "memory_fact_source",
    "memory_supersession",
)
COUNT_ROWS_SQL = "SELECT count(*) FROM {table}"


@dataclass(frozen=True)
class TemplateWorld:
    template_id: UUID
    scenario_id: UUID
    player_authored_id: UUID
    player_entity_id: UUID
    mira_authored_id: UUID
    mira_entity_id: UUID
    rank_fact: FactRow


@dataclass
class TurnSpec:
    sequence: int
    narration: str = ""
    action: str = ""
    deltas: list[AcceptedDeltaItem] = field(default_factory=list)
    rejected: list[RejectedCall] = field(default_factory=list)
    turn_id: UUID = field(default_factory=uuid4)
    participant_id: UUID = field(default_factory=uuid4)


async def create_template_entity(
    connection: AsyncConnection,
    template_id: UUID,
    name: str,
    *,
    is_player: bool = False,
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
    await add_template_alias(connection, template_id, entity.entity_id, name)
    return authored_id, entity.entity_id


async def add_template_alias(
    connection: AsyncConnection, template_id: UUID, entity_id: UUID, alias: str
) -> None:
    await entity_repo.add_aliases(
        connection,
        [
            AliasCreate(
                entity_id=entity_id,
                scope_kind="template",
                scope_id=template_id,
                alias=alias,
                alias_normalized=entity_repo.normalize_alias(alias),
            )
        ],
    )


async def create_template_row(connection: AsyncConnection, scenario_id: UUID) -> UUID:
    template = await template_repo.create_template(
        connection,
        TemplateCreate(
            scenario_id=scenario_id,
            publish_revision=PUBLISH_REVISION,
            mode="master",
            direct_status="ready",
            enrichment_status="not_needed",
            content_hash="hash",
        ),
    )
    return template.template_id


async def create_authored_fact(
    connection: AsyncConnection,
    template_id: UUID,
    subject_id: UUID,
    predicate: str,
    literal: str,
) -> FactRow:
    rows = await fact_repo.create_facts(
        connection,
        [
            FactCreate(
                scope_kind="template",
                scope_id=template_id,
                subject_entity_id=subject_id,
                predicate=predicate,
                object_literal=literal,
                authority="authored",
                assertion="occurred",
                valid_from_seq=0,
            )
        ],
    )
    return rows[0]


async def seed_template_world(connection: AsyncConnection) -> TemplateWorld:
    scenario_id = uuid4()
    template_id = await create_template_row(connection, scenario_id)
    player_authored, player_entity = await create_template_entity(
        connection, template_id, PLAYER_TEMPLATE_NAME, is_player=True
    )
    mira_authored, mira_entity = await create_template_entity(
        connection, template_id, "Mira"
    )
    rank_fact = await create_authored_fact(
        connection, template_id, mira_entity, "rank", f'"{INITIAL_RANK}"'
    )
    return TemplateWorld(
        template_id=template_id,
        scenario_id=scenario_id,
        player_authored_id=player_authored,
        player_entity_id=player_entity,
        mira_authored_id=mira_authored,
        mira_entity_id=mira_entity,
        rank_fact=rank_fact,
    )


def player_payload(
    authored_id: UUID, name: str, aliases: list[str] | None = None
) -> PlayerEntityPayload:
    return PlayerEntityPayload(
        authored_entity_id=authored_id,
        canonical_name=name,
        aliases=aliases or [],
        entity_type="character",
    )


def register_item(
    scenario_id: UUID,
    *,
    player: PlayerEntityPayload | None = None,
    setup_facts: list[SetupFactPayload] | None = None,
    publish_revision: int = PUBLISH_REVISION,
) -> RegisterItem:
    return RegisterItem(
        item_kind="register_playthrough",
        sequence=0,
        payload=RegisterPayload(
            scenario_id=scenario_id,
            publish_revision=publish_revision,
            player_entity=player,
            setup_facts=setup_facts or [],
        ),
    )


def turn_item(spec: TurnSpec) -> TurnItem:
    return TurnItem(
        item_kind="turn",
        sequence=spec.sequence,
        payload=TurnPayload(
            turn_id=spec.turn_id,
            turn_number=spec.sequence,
            participant_id=spec.participant_id,
            action_mode="do",
            action_text=spec.action,
            narration_text=spec.narration,
            accepted_delta=AcceptedDelta(items=spec.deltas),
            rejected_calls=spec.rejected,
        ),
    )


def flush_item(sequence: int) -> FlushItem:
    return FlushItem(item_kind="flush", sequence=sequence)


def mutation(key: str, after: object) -> AcceptedDeltaItem:
    return AcceptedDeltaItem(kind="state_mutation", key=key, after=after)


def build_request(
    playthrough_id: UUID, *items: RegisterItem | TurnItem | FlushItem
) -> IngestRequest:
    return IngestRequest(playthrough_id=playthrough_id, items=list(items))


async def count_rows(connection: AsyncConnection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in COUNTED_TABLES:
        statement = sql.SQL(COUNT_ROWS_SQL).format(table=sql.Identifier(table))
        cursor = await connection.execute(statement)
        row = await cursor.fetchone()
        assert row is not None
        counts[table] = int(row[0])
    return counts
