"""Builds and pushes a scenario's memory template (template-publish task 4).

Shared by the publish job and the rebuild script so both produce byte-identical
content for the same scenario: entities, facts, connections and cards are
sorted by id before hashing because the list queries have no ORDER BY.
"""

from __future__ import annotations

import hashlib
import json

from app.db.models.entity import Entity
from app.db.models.fact import Fact
from app.db.models.map_connection import MapConnection
from app.db.models.scenario import Scenario
from app.exceptions.memory_exceptions import MemoryTemplateBuildError
from app.integrations import memory_client
from app.models.memory_template import (
    MasterTemplateContent,
    NewbieTemplateContent,
    StoryCardPayload,
    TemplateBuildOutcome,
    TemplateBuildRequest,
    TemplateConnectionPayload,
    TemplateEntityPayload,
    TemplateFactPayload,
)
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.map_repo import MapRepo

MODE_MASTER = "master"
MODE_NEWBIE = "newbie"
STATUS_READY = "ready"
CODE_NOT_READY = "template_not_ready"

KEY_STORY_CARDS = "storyCards"
KEY_WORLD_LORE = "worldLore"
KEY_SINGLE_LORE_PROMPT = "singleLorePrompt"
KEY_MAIN_CONFLICT = "mainConflict"
KEY_OPENING_PROMPT = "openingPrompt"


async def push_template(
    scenario: Scenario,
    publish_revision: int,
    entity_repo: EntityRepo,
    fact_repo: FactRepo,
    map_repo: MapRepo,
) -> TemplateBuildOutcome:
    """Build the template for `publish_revision` in memory and require it ready."""
    request = await build_template_request(
        scenario, publish_revision, entity_repo, fact_repo, map_repo
    )
    outcome = await memory_client.build_template(request)
    if outcome.response.direct_status != STATUS_READY:
        raise MemoryTemplateBuildError(CODE_NOT_READY)
    return outcome


async def build_template_request(
    scenario: Scenario,
    publish_revision: int,
    entity_repo: EntityRepo,
    fact_repo: FactRepo,
    map_repo: MapRepo,
) -> TemplateBuildRequest:
    if scenario.mode == MODE_MASTER:
        master = await _build_master_content(scenario, entity_repo, fact_repo, map_repo)
        return TemplateBuildRequest(
            scenario_id=scenario.scenario_id,
            publish_revision=publish_revision,
            mode=MODE_MASTER,
            content_hash=compute_content_hash(master),
            master=master,
        )
    newbie = await _build_newbie_content(scenario, entity_repo, fact_repo)
    return TemplateBuildRequest(
        scenario_id=scenario.scenario_id,
        publish_revision=publish_revision,
        mode=MODE_NEWBIE,
        content_hash=compute_content_hash(newbie),
        newbie=newbie,
    )


def compute_content_hash(
    content: MasterTemplateContent | NewbieTemplateContent,
) -> str:
    canonical = json.dumps(
        _hashable_dump(content),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hashable_dump(
    content: MasterTemplateContent | NewbieTemplateContent,
) -> dict[str, object]:
    """A newbie template without cards or links hashes exactly as it did before
    those fields existed, so rebuilding an old revision is not seen as drift."""
    excluded: set[str] = set()
    if isinstance(content, NewbieTemplateContent):
        excluded = {
            name for name in ("entities", "facts") if not getattr(content, name)
        }
    return content.model_dump(mode="json", exclude=excluded)


async def _load_cards_and_links(
    scenario: Scenario, entity_repo: EntityRepo, fact_repo: FactRepo
) -> tuple[list[TemplateEntityPayload], list[TemplateFactPayload]]:
    entities = await entity_repo.list_by_scenario(scenario.scenario_id)
    facts = await fact_repo.list_by_scenario(scenario.scenario_id)
    return (
        sorted(
            (_to_entity_payload(e) for e in entities), key=lambda e: str(e.entity_id)
        ),
        sorted((_to_fact_payload(f) for f in facts), key=lambda f: str(f.fact_id)),
    )


async def _build_master_content(
    scenario: Scenario,
    entity_repo: EntityRepo,
    fact_repo: FactRepo,
    map_repo: MapRepo,
) -> MasterTemplateContent:
    entities, facts = await _load_cards_and_links(scenario, entity_repo, fact_repo)
    connections = await map_repo.list_connections_by_scenario(scenario.scenario_id)
    return MasterTemplateContent(
        entities=entities,
        facts=facts,
        map_connections=sorted(
            (_to_connection_payload(c) for c in connections),
            key=lambda c: str(c.connection_id),
        ),
    )


def _to_entity_payload(entity: Entity) -> TemplateEntityPayload:
    return TemplateEntityPayload(
        entity_id=entity.entity_id,
        entity_type=entity.entity_type,
        canonical_name=entity.canonical_name,
        aliases=list(entity.aliases),
        description=entity.description,
        is_player=entity.is_player,
    )


def _to_fact_payload(fact: Fact) -> TemplateFactPayload:
    return TemplateFactPayload(
        fact_id=fact.fact_id,
        subject_entity_id=fact.subject_entity_id,
        predicate=fact.predicate,
        object_entity_id=fact.object_entity_id,
        object_literal=fact.object_literal,
        when_active=fact.when_active,
        hidden=fact.hidden,
        superseded_fact_id=fact.superseded_fact_id,
    )


def _to_connection_payload(connection: MapConnection) -> TemplateConnectionPayload:
    return TemplateConnectionPayload(
        connection_id=connection.connection_id,
        entity_id_a=connection.entity_id_a,
        entity_id_b=connection.entity_id_b,
        label=connection.label,
    )


async def _build_newbie_content(
    scenario: Scenario, entity_repo: EntityRepo, fact_repo: FactRepo
) -> NewbieTemplateContent:
    world_data = scenario.world_data
    entities, facts = await _load_cards_and_links(scenario, entity_repo, fact_repo)
    return NewbieTemplateContent(
        entities=entities,
        facts=facts,
        story_cards=_build_story_cards(world_data.get(KEY_STORY_CARDS)),
        world_lore=_text_of(world_data.get(KEY_WORLD_LORE)),
        single_lore_prompt=_text_of(world_data.get(KEY_SINGLE_LORE_PROMPT)),
        main_conflict=_text_of(world_data.get(KEY_MAIN_CONFLICT)),
        opening_prompt=_text_of(world_data.get(KEY_OPENING_PROMPT)),
    )


def _build_story_cards(raw_cards: object) -> list[StoryCardPayload]:
    if not isinstance(raw_cards, list):
        return []
    cards = [_to_story_card(raw) for raw in raw_cards]
    return sorted(
        (card for card in cards if card is not None), key=lambda card: card.card_id
    )


def _to_story_card(raw: object) -> StoryCardPayload | None:
    if not isinstance(raw, dict):
        return None
    card_id = _text_of(raw.get("id"))
    name = _text_of(raw.get("name"))
    if not card_id or not name:
        return None
    return StoryCardPayload(
        card_id=card_id,
        type=_text_of(raw.get("type")),
        name=name,
        content=_text_of(raw.get("content")),
    )


def _text_of(value: object) -> str:
    return value if isinstance(value, str) else ""
