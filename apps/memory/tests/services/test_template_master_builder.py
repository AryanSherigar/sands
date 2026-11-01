"""Pure master-mode builders: entities, aliases, description and fact-text sources."""

from uuid import UUID, uuid4

from app.models.templates import (
    MasterTemplateContent,
    TemplateConnectionPayload,
    TemplateEntityPayload,
    TemplateFactPayload,
)
from app.services.template_master_builder import (
    build_alias_creates,
    build_description_sources,
    build_entity_creates,
    build_fact_plans,
)
from app.services.template_plans import SpanLimits

TEMPLATE_ID = uuid4()
LIMITS = SpanLimits(max_tokens=300, chars_per_token=3)


def _entity(name: str, **overrides: object) -> TemplateEntityPayload:
    fields: dict[str, object] = {
        "entity_id": uuid4(),
        "entity_type": "character",
        "canonical_name": name,
    }
    fields.update(overrides)
    return TemplateEntityPayload(**fields)


def _memory_ids(content: MasterTemplateContent) -> dict[UUID, UUID]:
    return {entity.entity_id: uuid4() for entity in content.entities}


def test_entity_creates_are_authored_template_rows() -> None:
    player = _entity("Hero", is_player=True)
    content = MasterTemplateContent(entities=[player, _entity("Mira")])

    rows = build_entity_creates(TEMPLATE_ID, content)

    assert [row.canonical_name for row in rows] == ["Hero", "Mira"]
    assert rows[0].authored_entity_id == player.entity_id
    assert rows[0].is_player is True
    assert rows[1].is_player is False
    for row in rows:
        assert (row.scope_kind, row.scope_id) == ("template", TEMPLATE_ID)
        assert (row.provenance, row.first_seen_seq) == ("authored", 0)


def test_aliases_include_canonical_name_and_are_deduplicated() -> None:
    entity = _entity("The Warden", aliases=["the warden", "It", "  ", "It"])
    content = MasterTemplateContent(entities=[entity])
    memory_ids = _memory_ids(content)

    rows = build_alias_creates(TEMPLATE_ID, content, memory_ids)

    assert [row.alias_normalized for row in rows] == ["the warden", "it"]
    assert {row.entity_id for row in rows} == {memory_ids[entity.entity_id]}
    assert all(row.scope_kind == "template" for row in rows)


def test_description_sources_use_per_entity_labels_and_skip_blank() -> None:
    described = _entity("Kestrel", description="A wandering scout.")
    blank = _entity("Ghost", description="   ")
    also_described = _entity("Warden", description="Undying guardian.")
    content = MasterTemplateContent(entities=[described, blank, also_described])
    memory_ids = _memory_ids(content)

    plans = build_description_sources(content, memory_ids, LIMITS)

    assert [plan.source_ref for plan in plans] == [
        str(described.entity_id),
        str(also_described.entity_id),
    ]
    assert all(plan.source_kind == "authored_description" for plan in plans)
    assert [plan.spans[0].draft.label for plan in plans] == ["D1.1", "D3.1"]
    assert plans[0].spans[0].entity_ids == [memory_ids[described.entity_id]]


def test_fact_plan_carries_flags_chain_and_readable_text() -> None:
    warden, sigil = _entity("The Warden"), _entity("Ember Sigil")
    old_fact_id, new_fact_id = uuid4(), uuid4()
    old = TemplateFactPayload(
        fact_id=old_fact_id,
        subject_entity_id=warden.entity_id,
        predicate="vulnerable_to",
        object_entity_id=sigil.entity_id,
        hidden=True,
    )
    new = TemplateFactPayload(
        fact_id=new_fact_id,
        subject_entity_id=warden.entity_id,
        predicate="rank",
        object_literal="Warden Prime",
        when_active={"field": "flags.a", "op": "==", "value": True},
        superseded_fact_id=old_fact_id,
    )
    content = MasterTemplateContent(entities=[warden, sigil], facts=[old, new])
    memory_ids = _memory_ids(content)

    old_plan, new_plan = build_fact_plans(TEMPLATE_ID, content, memory_ids, LIMITS)

    assert old_plan.source.content == "The Warden vulnerable to Ember Sigil"
    assert old_plan.source.source_kind == "authored_fact_text"
    assert old_plan.source.source_ref == str(old_fact_id)
    assert old_plan.fact.is_hidden is True
    assert old_plan.fact.conditional is False
    assert old_plan.fact.object_entity_id == memory_ids[sigil.entity_id]
    assert old_plan.fact.subject_entity_id == memory_ids[warden.entity_id]
    old_span = old_plan.source.spans[0]
    assert old_span.draft.label == "F1.1"
    assert old_span.is_hidden is True
    assert old_span.authored_fact_id == old_fact_id
    assert set(old_span.entity_ids) == {
        memory_ids[warden.entity_id],
        memory_ids[sigil.entity_id],
    }
    assert new_plan.fact.conditional is True
    assert new_plan.fact.object_literal == "Warden Prime"
    assert new_plan.fact.supersedes_authored_fact_id == old_fact_id
    assert new_plan.source.spans[0].conditional is True
    assert new_plan.source.spans[0].draft.label == "F2.1"
    for plan in (old_plan, new_plan):
        assert plan.fact.authority == "authored"
        assert plan.fact.assertion == "occurred"
        assert plan.fact.valid_from_seq == 0
        assert plan.fact.authored_fact_id == plan.source.spans[0].authored_fact_id
        assert (plan.fact.scope_kind, plan.fact.scope_id) == ("template", TEMPLATE_ID)


def test_connections_become_connects_to_facts_after_authored_facts() -> None:
    village, cairn = _entity("Ashfall"), _entity("Hollow Cairn")
    fact = TemplateFactPayload(
        fact_id=uuid4(),
        subject_entity_id=village.entity_id,
        predicate="is_a",
        object_literal="village",
    )
    connection = TemplateConnectionPayload(
        connection_id=uuid4(),
        entity_id_a=village.entity_id,
        entity_id_b=cairn.entity_id,
        label="mountain pass",
    )
    unlabeled = TemplateConnectionPayload(
        connection_id=uuid4(),
        entity_id_a=cairn.entity_id,
        entity_id_b=village.entity_id,
    )
    content = MasterTemplateContent(
        entities=[village, cairn], facts=[fact], map_connections=[connection, unlabeled]
    )
    memory_ids = _memory_ids(content)

    plans = build_fact_plans(TEMPLATE_ID, content, memory_ids, LIMITS)

    assert len(plans) == 3
    labeled, plain = plans[1], plans[2]
    assert labeled.source.content == "Ashfall connects to Hollow Cairn (mountain pass)"
    assert plain.source.content == "Hollow Cairn connects to Ashfall"
    assert labeled.fact.predicate == "connects_to"
    assert labeled.fact.authored_fact_id == connection.connection_id
    assert labeled.fact.object_entity_id == memory_ids[cairn.entity_id]
    assert labeled.fact.is_hidden is False and labeled.fact.conditional is False
    assert [plan.source.spans[0].draft.label for plan in plans] == [
        "F1.1",
        "F2.1",
        "F3.1",
    ]


def test_long_fact_text_splits_into_labelled_spans_without_truncation() -> None:
    entity = _entity("Chronicler")
    long_text = ". ".join(f"Sentence number {i} is here" for i in range(200)) + "."
    fact = TemplateFactPayload(
        fact_id=uuid4(),
        subject_entity_id=entity.entity_id,
        predicate="wrote",
        object_literal=long_text,
    )
    content = MasterTemplateContent(entities=[entity], facts=[fact])

    plan = build_fact_plans(TEMPLATE_ID, content, _memory_ids(content), LIMITS)[0]

    labels = [span.draft.label for span in plan.source.spans]
    assert len(labels) > 1
    assert labels == [f"F1.{k}" for k in range(1, len(labels) + 1)]
    assert plan.source.spans[-1].draft.end_offset == len(plan.source.content)
