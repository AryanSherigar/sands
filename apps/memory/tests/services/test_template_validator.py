"""Pure validation of a template build request; nothing here touches the database."""

from uuid import UUID, uuid4

import pytest
from app.exceptions.template_exceptions import TemplateValidationError
from app.models.templates import (
    MasterTemplateContent,
    NewbieTemplateContent,
    StoryCardPayload,
    TemplateBuildRequest,
    TemplateConnectionPayload,
    TemplateEntityPayload,
    TemplateFactPayload,
)
from app.services.template_validator import validate_template_request

HOLLOW_CAIRN_ENTITY_COUNT = 7
CONTENT_HASH = "hash"


def _entity(entity_id: UUID | None = None, *, is_player: bool = False):
    return TemplateEntityPayload(
        entity_id=entity_id or uuid4(),
        entity_type="character",
        canonical_name="Someone",
        is_player=is_player,
    )


def _fact(subject: UUID, **overrides: object) -> TemplateFactPayload:
    fields: dict[str, object] = {
        "fact_id": uuid4(),
        "subject_entity_id": subject,
        "predicate": "rank",
        "object_literal": "knight",
    }
    fields.update(overrides)
    return TemplateFactPayload(**fields)


def _master_request(content: MasterTemplateContent) -> TemplateBuildRequest:
    return TemplateBuildRequest(
        scenario_id=uuid4(),
        publish_revision=1,
        mode="master",
        content_hash=CONTENT_HASH,
        master=content,
    )


def _newbie_request(content: NewbieTemplateContent) -> TemplateBuildRequest:
    return TemplateBuildRequest(
        scenario_id=uuid4(),
        publish_revision=1,
        mode="newbie",
        content_hash=CONTENT_HASH,
        newbie=content,
    )


def _assert_rejected(request: TemplateBuildRequest) -> None:
    with pytest.raises(TemplateValidationError) as caught:
        validate_template_request(request)
    assert caught.value.status_code == 422
    assert caught.value.code == "invalid_template"


def test_valid_master_request_passes() -> None:
    entities = [_entity() for _ in range(HOLLOW_CAIRN_ENTITY_COUNT)]
    facts = [_fact(entity.entity_id) for entity in entities]
    facts[0] = _fact(
        entities[0].entity_id,
        object_literal=None,
        object_entity_id=entities[1].entity_id,
        hidden=True,
        when_active={"field": "flags.a", "op": "==", "value": True},
    )
    connection = TemplateConnectionPayload(
        connection_id=uuid4(),
        entity_id_a=entities[0].entity_id,
        entity_id_b=entities[1].entity_id,
        label="mountain pass",
    )

    validate_template_request(
        _master_request(
            MasterTemplateContent(
                entities=entities, facts=facts, map_connections=[connection]
            )
        )
    )


def test_empty_master_and_empty_newbie_are_valid() -> None:
    validate_template_request(_master_request(MasterTemplateContent()))
    validate_template_request(_newbie_request(NewbieTemplateContent()))


def test_valid_newbie_request_passes() -> None:
    cards = [
        StoryCardPayload(card_id=f"card-{i}", type="Character", name="N", content="c")
        for i in range(3)
    ]

    validate_template_request(
        _newbie_request(NewbieTemplateContent(story_cards=cards, world_lore="Lore."))
    )


def test_newbie_entities_and_facts_are_validated_like_master() -> None:
    entity = _entity()
    valid = NewbieTemplateContent(entities=[entity], facts=[_fact(entity.entity_id)])
    unknown_subject = NewbieTemplateContent(entities=[entity], facts=[_fact(uuid4())])
    two_players = NewbieTemplateContent(
        entities=[_entity(is_player=True), _entity(is_player=True)]
    )
    shared_id = uuid4()
    duplicate_entities = NewbieTemplateContent(
        entities=[_entity(shared_id), _entity(shared_id)]
    )

    validate_template_request(_newbie_request(valid))
    for content in (unknown_subject, two_players, duplicate_entities):
        _assert_rejected(_newbie_request(content))


def test_mode_and_content_must_agree() -> None:
    master_with_newbie = _master_request(MasterTemplateContent())
    master_with_newbie.newbie = NewbieTemplateContent()
    newbie_with_master = _newbie_request(NewbieTemplateContent())
    newbie_with_master.master = MasterTemplateContent()
    master_without_content = _master_request(MasterTemplateContent())
    master_without_content.master = None
    newbie_without_content = _newbie_request(NewbieTemplateContent())
    newbie_without_content.newbie = None

    for request in (
        master_with_newbie,
        newbie_with_master,
        master_without_content,
        newbie_without_content,
    ):
        _assert_rejected(request)


def test_duplicate_ids_are_rejected() -> None:
    shared_id = uuid4()
    entity = _entity()
    duplicate_entities = MasterTemplateContent(
        entities=[_entity(shared_id), _entity(shared_id)]
    )
    duplicate_facts = MasterTemplateContent(
        entities=[entity],
        facts=[_fact(entity.entity_id, fact_id=shared_id)] * 2,
    )
    connection = TemplateConnectionPayload(
        connection_id=shared_id,
        entity_id_a=entity.entity_id,
        entity_id_b=entity.entity_id,
    )
    duplicate_connections = MasterTemplateContent(
        entities=[entity], map_connections=[connection, connection]
    )
    card = StoryCardPayload(card_id="same", type="item", name="N", content="c")
    duplicate_cards = NewbieTemplateContent(story_cards=[card, card])

    for content in (duplicate_entities, duplicate_facts, duplicate_connections):
        _assert_rejected(_master_request(content))
    _assert_rejected(_newbie_request(duplicate_cards))


def test_a_fact_id_may_not_collide_with_a_connection_id() -> None:
    entity = _entity()
    shared_id = uuid4()
    content = MasterTemplateContent(
        entities=[entity],
        facts=[_fact(entity.entity_id, fact_id=shared_id)],
        map_connections=[
            TemplateConnectionPayload(
                connection_id=shared_id,
                entity_id_a=entity.entity_id,
                entity_id_b=entity.entity_id,
            )
        ],
    )

    _assert_rejected(_master_request(content))


def test_dangling_references_are_rejected() -> None:
    entity = _entity()
    stranger = uuid4()
    dangling_subject = MasterTemplateContent(entities=[entity], facts=[_fact(stranger)])
    dangling_object = MasterTemplateContent(
        entities=[entity],
        facts=[_fact(entity.entity_id, object_literal=None, object_entity_id=stranger)],
    )
    dangling_connection = MasterTemplateContent(
        entities=[entity],
        map_connections=[
            TemplateConnectionPayload(
                connection_id=uuid4(),
                entity_id_a=entity.entity_id,
                entity_id_b=stranger,
            )
        ],
    )
    dangling_chain = MasterTemplateContent(
        entities=[entity],
        facts=[_fact(entity.entity_id, superseded_fact_id=uuid4())],
    )

    for content in (
        dangling_subject,
        dangling_object,
        dangling_connection,
        dangling_chain,
    ):
        _assert_rejected(_master_request(content))


def test_fact_needs_exactly_one_object() -> None:
    entity = _entity()
    both = _fact(entity.entity_id, object_entity_id=entity.entity_id)
    neither = _fact(entity.entity_id, object_literal=None)

    for fact in (both, neither):
        _assert_rejected(
            _master_request(MasterTemplateContent(entities=[entity], facts=[fact]))
        )


def test_supersession_self_link_and_cycle_are_rejected() -> None:
    entity = _entity()
    first_id, second_id = uuid4(), uuid4()
    self_link = _fact(entity.entity_id, fact_id=first_id, superseded_fact_id=first_id)
    cycle = [
        _fact(entity.entity_id, fact_id=first_id, superseded_fact_id=second_id),
        _fact(entity.entity_id, fact_id=second_id, superseded_fact_id=first_id),
    ]

    _assert_rejected(
        _master_request(MasterTemplateContent(entities=[entity], facts=[self_link]))
    )
    _assert_rejected(
        _master_request(MasterTemplateContent(entities=[entity], facts=cycle))
    )


def test_a_valid_supersession_chain_passes() -> None:
    entity = _entity()
    old_id, new_id = uuid4(), uuid4()
    facts = [
        _fact(entity.entity_id, fact_id=old_id, object_literal="squire"),
        _fact(entity.entity_id, fact_id=new_id, superseded_fact_id=old_id),
    ]

    validate_template_request(
        _master_request(MasterTemplateContent(entities=[entity], facts=facts))
    )


def test_more_than_one_player_entity_is_rejected() -> None:
    content = MasterTemplateContent(
        entities=[_entity(is_player=True), _entity(is_player=True)]
    )

    _assert_rejected(_master_request(content))


def test_validation_reason_never_contains_prose() -> None:
    secret_prose = "The Warden secretly fears the sigil."
    entity = _entity()
    fact = _fact(
        entity.entity_id, object_literal=secret_prose, object_entity_id=uuid4()
    )

    with pytest.raises(TemplateValidationError) as caught:
        validate_template_request(
            _master_request(MasterTemplateContent(entities=[entity], facts=[fact]))
        )

    assert secret_prose not in caught.value.message
