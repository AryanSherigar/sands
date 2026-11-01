"""Pure newbie-mode builders: card entities, card sources and lore sources."""

from uuid import UUID, uuid4, uuid5

from app.models.templates import (
    NewbieTemplateContent,
    StoryCardPayload,
    TemplateEntityPayload,
)
from app.services.entity_tagger import build_alias_index
from app.services.template_newbie_builder import (
    authored_graph_of,
    build_card_alias_creates,
    build_card_entity_creates,
    build_card_sources,
    build_lore_sources,
    card_authored_entity_id,
    normalize_card_type,
)
from app.services.template_plans import SpanLimits

TEMPLATE_ID = uuid4()
SCENARIO_ID = uuid4()
LIMITS = SpanLimits(max_tokens=300, chars_per_token=3)


def _card(
    card_id: str, name: str, type_: str = "Character", content: str = "text."
) -> StoryCardPayload:
    return StoryCardPayload(card_id=card_id, type=type_, name=name, content=content)


def _memory_ids(content: NewbieTemplateContent) -> dict[UUID, UUID]:
    return {
        card_authored_entity_id(SCENARIO_ID, card.card_id): uuid4()
        for card in content.story_cards
    }


def _alias_index(content: NewbieTemplateContent, memory_ids: dict[UUID, UUID]):
    aliases = build_card_alias_creates(TEMPLATE_ID, SCENARIO_ID, content, memory_ids)
    return build_alias_index([(row.alias_normalized, row.entity_id) for row in aliases])


def test_authored_entity_id_is_deterministic_uuid5() -> None:
    assert card_authored_entity_id(SCENARIO_ID, "card-1") == uuid5(
        SCENARIO_ID, "card-1"
    )
    assert card_authored_entity_id(SCENARIO_ID, "card-1") != card_authored_entity_id(
        uuid4(), "card-1"
    )


def test_card_types_are_normalized() -> None:
    assert normalize_card_type("Character") == "character"
    assert normalize_card_type(" FACTION ") == "faction"
    assert normalize_card_type("Location") == "location"
    assert normalize_card_type("item") == "item"
    assert normalize_card_type("Spell") == "other"
    assert normalize_card_type("") == "other"


def test_card_entities_are_authored_and_blank_names_are_skipped() -> None:
    content = NewbieTemplateContent(
        story_cards=[
            _card("a", "Mira"),
            _card("b", "   "),
            _card("c", "Guild", "Faction"),
        ]
    )

    rows = build_card_entity_creates(TEMPLATE_ID, SCENARIO_ID, content)

    assert [(row.canonical_name, row.entity_type) for row in rows] == [
        ("Mira", "character"),
        ("Guild", "faction"),
    ]
    assert rows[0].authored_entity_id == card_authored_entity_id(SCENARIO_ID, "a")
    for row in rows:
        assert (row.scope_kind, row.scope_id) == ("template", TEMPLATE_ID)
        assert (row.provenance, row.first_seen_seq, row.is_player) == (
            "authored",
            0,
            False,
        )


def test_card_alias_is_the_normalized_name() -> None:
    content = NewbieTemplateContent(story_cards=[_card("a", "The Red Guild")])
    memory_ids = _memory_ids(content)

    rows = build_card_alias_creates(TEMPLATE_ID, SCENARIO_ID, content, memory_ids)

    assert [(row.alias, row.alias_normalized) for row in rows] == [
        ("The Red Guild", "the red guild")
    ]


def test_card_sources_tag_own_and_other_cards_with_per_card_labels() -> None:
    content = NewbieTemplateContent(
        story_cards=[
            _card("a", "Mira", content="Mira serves the Red Guild."),
            _card("b", "Red Guild", "Faction", content="Ruled from Ashfall."),
            _card("c", "Nameless", content=""),
        ]
    )
    memory_ids = _memory_ids(content)
    index = _alias_index(content, memory_ids)
    mira = memory_ids[card_authored_entity_id(SCENARIO_ID, "a")]
    guild = memory_ids[card_authored_entity_id(SCENARIO_ID, "b")]

    plans = build_card_sources(SCENARIO_ID, content, memory_ids, index, LIMITS)

    assert [plan.source_ref for plan in plans] == ["a", "b"]
    assert all(plan.source_kind == "authored_card" for plan in plans)
    assert plans[0].spans[0].draft.label == "C1.1"
    assert plans[1].spans[0].draft.label == "C2.1"
    assert set(plans[0].spans[0].entity_ids) == {mira, guild}
    assert plans[1].spans[0].entity_ids == [guild]


def test_lore_sources_share_one_running_label_counter_in_fixed_field_order() -> None:
    content = NewbieTemplateContent(
        world_lore="First paragraph.\n\nSecond paragraph.",
        single_lore_prompt="",
        main_conflict="The conflict.",
        opening_prompt="The opening.",
    )

    plans = build_lore_sources(content, {}, LIMITS)

    assert [plan.source_ref for plan in plans] == [
        "world_lore",
        "main_conflict",
        "opening_prompt",
    ]
    assert all(plan.source_kind == "authored_lore" for plan in plans)
    labels = [span.draft.label for plan in plans for span in plan.spans]
    assert labels == ["L1", "L2", "L3", "L4"]
    ordinals = [span.draft.ordinal for span in plans[0].spans]
    assert ordinals == [1, 2]


def test_lore_spans_are_tagged_by_exact_alias_match() -> None:
    content = NewbieTemplateContent(
        story_cards=[_card("a", "Mira")],
        world_lore="Mira crossed the river. Nobody else.",
    )
    memory_ids = _memory_ids(content)
    index = _alias_index(content, memory_ids)

    plans = build_lore_sources(content, index, LIMITS)

    assert plans[0].spans[0].entity_ids == [
        memory_ids[card_authored_entity_id(SCENARIO_ID, "a")]
    ]


def test_empty_content_produces_no_plans() -> None:
    content = NewbieTemplateContent()

    assert build_card_entity_creates(TEMPLATE_ID, SCENARIO_ID, content) == []
    assert build_card_sources(SCENARIO_ID, content, {}, {}, LIMITS) == []
    assert build_lore_sources(content, {}, LIMITS) == []


def _entity(name: str, entity_id: UUID | None = None) -> TemplateEntityPayload:
    return TemplateEntityPayload(
        entity_id=entity_id or uuid4(), entity_type="character", canonical_name=name
    )


def test_cards_matching_an_entity_by_derived_id_or_name_are_dropped() -> None:
    content = NewbieTemplateContent(
        story_cards=[
            _card("a", "Mira", content="Same id."),
            _card("b", "  RED guild ", "Faction", content="Same name."),
            _card("c", "Ashfall", "Location", content="Kept."),
        ],
        entities=[
            _entity("Mira the Bold", card_authored_entity_id(SCENARIO_ID, "a")),
            _entity("Red Guild"),
        ],
    )
    memory_ids = _memory_ids(content)

    entity_rows = build_card_entity_creates(TEMPLATE_ID, SCENARIO_ID, content)
    alias_rows = build_card_alias_creates(TEMPLATE_ID, SCENARIO_ID, content, memory_ids)
    plans = build_card_sources(SCENARIO_ID, content, memory_ids, {}, LIMITS)

    assert [row.canonical_name for row in entity_rows] == ["Ashfall"]
    assert [row.alias for row in alias_rows] == ["Ashfall"]
    assert [plan.source_ref for plan in plans] == ["c"]


def test_authored_graph_carries_only_entities_and_facts() -> None:
    entity = _entity("Mira")
    content = NewbieTemplateContent(
        story_cards=[_card("a", "Card")], entities=[entity], world_lore="Lore."
    )

    graph = authored_graph_of(content)

    assert graph.entities == [entity]
    assert graph.facts == []
    assert graph.map_connections == []
