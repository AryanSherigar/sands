"""Request builders and row counters for template direct-write tests."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.models.templates import (
    MasterTemplateContent,
    NewbieTemplateContent,
    StoryCardPayload,
    TemplateBuildRequest,
    TemplateConnectionPayload,
    TemplateEntityPayload,
    TemplateFactPayload,
)
from psycopg import AsyncConnection

DEFAULT_REVISION = 1
DEFAULT_HASH = "hash-1"
WARDEN_CONDITION: dict[str, object] = {
    "field": "flags.rescued",
    "op": "==",
    "value": True,
}

HOLLOW_CAIRN_ENTITIES: tuple[tuple[str, str, str, list[str], str], ...] = (
    (
        "kestrel_vane",
        "character",
        "Kestrel Vane",
        ["Kestrel", "the Scout"],
        "A former cairn-warden's apprentice, now a wandering scout.",
    ),
    (
        "the_warden",
        "character",
        "The Warden",
        ["the Warden", "It"],
        "The cairn's undying guardian. Speaks rarely.",
    ),
    (
        "hollow_cairn",
        "location",
        "The Hollow Cairn",
        [],
        "A barrow sunk into the hill.",
    ),
    ("ashfall_village", "location", "Ashfall Village", [], "A burned-out village."),
    ("the_vigil", "faction", "The Vigil", [], "A dwindling order sworn to the cairn."),
    ("ember_sigil", "item", "Ember Sigil", ["the sigil"], "A warded relic."),
    ("rustbound_blade", "item", "Rustbound Blade", [], "A plain sword."),
)

EDGE_FACTS: tuple[tuple[str, str, str, bool, bool], ...] = (
    ("kestrel_vane", "member_of", "the_vigil", False, False),
    ("kestrel_vane", "located_at", "ashfall_village", False, True),
    ("kestrel_vane", "located_at", "hollow_cairn", False, True),
    ("the_warden", "located_at", "hollow_cairn", False, False),
    ("the_warden", "guards", "hollow_cairn", False, False),
    ("the_warden", "vulnerable_to", "ember_sigil", True, False),
    ("hollow_cairn", "entrance_guarded_by", "the_vigil", False, False),
)

SELECT_TEMPLATE_ROW_COUNT = (
    "SELECT count(*) FROM memory_template WHERE scenario_id = %s"
)
SCOPED_COUNT_SQL = {
    "memory_entity": "SELECT count(*) FROM memory_entity WHERE scope_kind = 'template' AND scope_id = %s",
    "memory_alias": "SELECT count(*) FROM memory_alias WHERE scope_kind = 'template' AND scope_id = %s",
    "memory_source": "SELECT count(*) FROM memory_source WHERE scope_kind = 'template' AND scope_id = %s",
    "memory_span": "SELECT count(*) FROM memory_span WHERE scope_kind = 'template' AND scope_id = %s",
    "memory_fact": "SELECT count(*) FROM memory_fact WHERE scope_kind = 'template' AND scope_id = %s",
    "memory_embedding": "SELECT count(*) FROM memory_embedding WHERE scope_kind = 'template' AND scope_id = %s",
    "memory_extraction_batch": "SELECT count(*) FROM memory_extraction_batch WHERE scope_kind = 'template' AND scope_id = %s",
}
COUNT_FACT_SOURCES_SQL = (
    "SELECT count(*) FROM memory_fact_source AS link "
    "JOIN memory_fact AS fact ON fact.fact_id = link.fact_id "
    "WHERE fact.scope_kind = 'template' AND fact.scope_id = %s"
)
COUNT_HIDDEN_FACTS_SQL = (
    "SELECT count(*) FROM memory_fact "
    "WHERE scope_kind = 'template' AND scope_id = %s AND is_hidden"
)
COUNT_CONDITIONAL_FACTS_SQL = (
    "SELECT count(*) FROM memory_fact "
    "WHERE scope_kind = 'template' AND scope_id = %s AND conditional"
)


@dataclass(frozen=True)
class HollowCairn:
    request: TemplateBuildRequest
    ids: dict[str, UUID]


def build_hollow_cairn(
    scenario_id: UUID | None = None,
    publish_revision: int = DEFAULT_REVISION,
    content_hash: str = DEFAULT_HASH,
) -> HollowCairn:
    ids = {slug: uuid4() for slug, *_rest in HOLLOW_CAIRN_ENTITIES}
    entities = [
        TemplateEntityPayload(
            entity_id=ids[slug],
            entity_type=entity_type,
            canonical_name=name,
            aliases=aliases,
            description=description,
        )
        for slug, entity_type, name, aliases, description in HOLLOW_CAIRN_ENTITIES
    ]
    facts = [
        TemplateFactPayload(
            fact_id=uuid4(),
            subject_entity_id=ids[subject],
            predicate=predicate,
            object_entity_id=ids[target],
            hidden=is_hidden,
            when_active=WARDEN_CONDITION if is_conditional else None,
        )
        for subject, predicate, target, is_hidden, is_conditional in EDGE_FACTS
    ]
    request = TemplateBuildRequest(
        scenario_id=scenario_id or uuid4(),
        publish_revision=publish_revision,
        mode="master",
        content_hash=content_hash,
        master=MasterTemplateContent(entities=entities, facts=facts),
    )
    return HollowCairn(request=request, ids=ids)


def build_newbie_request(
    cards: list[StoryCardPayload],
    *,
    world_lore: str = "",
    scenario_id: UUID | None = None,
    publish_revision: int = DEFAULT_REVISION,
    content_hash: str = DEFAULT_HASH,
) -> TemplateBuildRequest:
    return TemplateBuildRequest(
        scenario_id=scenario_id or uuid4(),
        publish_revision=publish_revision,
        mode="newbie",
        content_hash=content_hash,
        newbie=NewbieTemplateContent(story_cards=cards, world_lore=world_lore),
    )


def build_newbie_graph_request(
    *,
    cards: list[StoryCardPayload] | None = None,
    entities: list[TemplateEntityPayload] | None = None,
    facts: list[TemplateFactPayload] | None = None,
    world_lore: str = "",
    scenario_id: UUID | None = None,
) -> TemplateBuildRequest:
    return TemplateBuildRequest(
        scenario_id=scenario_id or uuid4(),
        publish_revision=DEFAULT_REVISION,
        mode="newbie",
        content_hash=DEFAULT_HASH,
        newbie=NewbieTemplateContent(
            story_cards=cards or [],
            entities=entities or [],
            facts=facts or [],
            world_lore=world_lore,
        ),
    )


def story_card(
    card_id: str, name: str, card_type: str, content: str
) -> StoryCardPayload:
    return StoryCardPayload(card_id=card_id, type=card_type, name=name, content=content)


def connection_between(entity_a: UUID, entity_b: UUID, label: str | None = None):
    return TemplateConnectionPayload(
        connection_id=uuid4(), entity_id_a=entity_a, entity_id_b=entity_b, label=label
    )


async def _count(connection: AsyncConnection, statement: str, parameter: UUID) -> int:
    cursor = await connection.execute(statement, (parameter,))
    row = await cursor.fetchone()
    assert row is not None
    return int(row[0])


async def scoped_counts(
    connection: AsyncConnection, template_id: UUID
) -> dict[str, int]:
    counts = {
        table: await _count(connection, statement, template_id)
        for table, statement in SCOPED_COUNT_SQL.items()
    }
    counts["memory_fact_source"] = await _count(
        connection, COUNT_FACT_SOURCES_SQL, template_id
    )
    return counts


async def hidden_fact_count(connection: AsyncConnection, template_id: UUID) -> int:
    return await _count(connection, COUNT_HIDDEN_FACTS_SQL, template_id)


async def conditional_fact_count(connection: AsyncConnection, template_id: UUID) -> int:
    return await _count(connection, COUNT_CONDITIONAL_FACTS_SQL, template_id)


async def template_row_count(connection: AsyncConnection, scenario_id: UUID) -> int:
    return await _count(connection, SELECT_TEMPLATE_ROW_COUNT, scenario_id)
