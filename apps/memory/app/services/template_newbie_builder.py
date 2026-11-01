"""Pure builders for a newbie template: card entities, card sources and lore sources."""

from uuid import UUID, uuid5

from app.models.facts import AliasCreate, EntityCreate
from app.models.templates import (
    MasterTemplateContent,
    NewbieTemplateContent,
    StoryCardPayload,
)
from app.repositories.entity_repo import normalize_alias
from app.services.entity_tagger import tag_entities
from app.services.ingest_common import TEMPLATE_SCOPE
from app.services.span_splitter import split_spans
from app.services.template_plans import SourcePlan, SpanLimits, SpanPlan

AUTHORED_SEQUENCE = 0
KNOWN_CARD_TYPES = frozenset({"character", "faction", "location", "item"})
OTHER_CARD_TYPE = "other"
CARD_LABEL_PREFIX = "C"
LORE_LABEL_PREFIX = "L"


def card_authored_entity_id(scenario_id: UUID, card_id: str) -> UUID:
    return uuid5(scenario_id, card_id)


def normalize_card_type(raw_type: str) -> str:
    card_type = raw_type.strip().casefold()
    if card_type in KNOWN_CARD_TYPES:
        return card_type
    return OTHER_CARD_TYPE


def authored_graph_of(content: NewbieTemplateContent) -> MasterTemplateContent:
    return MasterTemplateContent(entities=content.entities, facts=content.facts)


def _cards_without_entity(
    scenario_id: UUID, content: NewbieTemplateContent
) -> list[StoryCardPayload]:
    """Entities supersede the legacy cards they were migrated from, matched by the
    card's derived id or, for hand-authored duplicates, by canonical name."""
    entity_ids = {entity.entity_id for entity in content.entities}
    entity_names = {
        normalize_alias(entity.canonical_name)
        for entity in content.entities
        if entity.canonical_name.strip()
    }
    return [
        card
        for card in content.story_cards
        if card_authored_entity_id(scenario_id, card.card_id) not in entity_ids
        and normalize_alias(card.name) not in entity_names
    ]


def _named_cards(
    scenario_id: UUID, content: NewbieTemplateContent
) -> list[StoryCardPayload]:
    return [
        card
        for card in _cards_without_entity(scenario_id, content)
        if card.name.strip()
    ]


def build_card_entity_creates(
    template_id: UUID, scenario_id: UUID, content: NewbieTemplateContent
) -> list[EntityCreate]:
    return [
        EntityCreate(
            scope_kind=TEMPLATE_SCOPE,
            scope_id=template_id,
            authored_entity_id=card_authored_entity_id(scenario_id, card.card_id),
            entity_type=normalize_card_type(card.type),
            canonical_name=card.name,
            provenance="authored",
            first_seen_seq=AUTHORED_SEQUENCE,
        )
        for card in _named_cards(scenario_id, content)
    ]


def build_card_alias_creates(
    template_id: UUID,
    scenario_id: UUID,
    content: NewbieTemplateContent,
    entity_ids: dict[UUID, UUID],
) -> list[AliasCreate]:
    return [
        AliasCreate(
            entity_id=entity_ids[card_authored_entity_id(scenario_id, card.card_id)],
            scope_kind=TEMPLATE_SCOPE,
            scope_id=template_id,
            alias=card.name,
            alias_normalized=normalize_alias(card.name),
        )
        for card in _named_cards(scenario_id, content)
    ]


def build_card_sources(
    scenario_id: UUID,
    content: NewbieTemplateContent,
    entity_ids: dict[UUID, UUID],
    alias_index: dict[str, set[UUID]],
    limits: SpanLimits,
) -> list[SourcePlan]:
    plans: list[SourcePlan] = []
    for index, card in enumerate(_cards_without_entity(scenario_id, content), start=1):
        if not card.content.strip():
            continue
        own_entity_id = entity_ids.get(
            card_authored_entity_id(scenario_id, card.card_id)
        )
        drafts = split_spans(
            card.content,
            f"{CARD_LABEL_PREFIX}{index}",
            limits.max_tokens,
            limits.chars_per_token,
        )
        spans = [
            SpanPlan(draft, _tagged_entity_ids(draft.text, own_entity_id, alias_index))
            for draft in drafts
        ]
        plans.append(SourcePlan("authored_card", card.card_id, card.content, spans))
    return plans


def _tagged_entity_ids(
    text: str, own_entity_id: UUID | None, alias_index: dict[str, set[UUID]]
) -> list[UUID]:
    tagged = set(tag_entities(text, alias_index))
    if own_entity_id is not None:
        tagged.add(own_entity_id)
    return sorted(tagged, key=str)


def _lore_fields(content: NewbieTemplateContent) -> list[tuple[str, str]]:
    return [
        ("world_lore", content.world_lore),
        ("single_lore_prompt", content.single_lore_prompt),
        ("main_conflict", content.main_conflict),
        ("opening_prompt", content.opening_prompt),
    ]


def build_lore_sources(
    content: NewbieTemplateContent,
    alias_index: dict[str, set[UUID]],
    limits: SpanLimits,
) -> list[SourcePlan]:
    plans: list[SourcePlan] = []
    label_number = 0
    for field_name, text in _lore_fields(content):
        if not text.strip():
            continue
        spans = _lore_spans(text, label_number, alias_index, limits)
        label_number += len(spans)
        plans.append(SourcePlan("authored_lore", field_name, text, spans))
    return plans


def _lore_spans(
    text: str,
    labels_used: int,
    alias_index: dict[str, set[UUID]],
    limits: SpanLimits,
) -> list[SpanPlan]:
    drafts = split_spans(
        text, LORE_LABEL_PREFIX, limits.max_tokens, limits.chars_per_token
    )
    return [
        SpanPlan(
            draft.model_copy(
                update={"label": f"{LORE_LABEL_PREFIX}{labels_used + offset}"}
            ),
            tag_entities(draft.text, alias_index),
        )
        for offset, draft in enumerate(drafts, start=1)
    ]
