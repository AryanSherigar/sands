"""template_service against a real Postgres: direct writes, idempotency, atomicity."""

import asyncio
from uuid import uuid4

import pytest
import structlog
from app.exceptions.template_exceptions import (
    TemplateContentConflictError,
    TemplateValidationError,
)
from app.logging import configure_logging
from app.models.templates import (
    MasterTemplateContent,
    TemplateBuildRequest,
    TemplateEntityPayload,
    TemplateFactPayload,
)
from app.repositories import entity_repo, fact_repo, playthrough_repo, span_repo
from app.services import template_service
from app.services.ingest_service import IngestService
from app.services.template_newbie_builder import card_authored_entity_id
from app.services.template_service import TemplateService
from psycopg import AsyncConnection
from tests.services.ingest_helpers import build_request, register_item
from tests.services.template_helpers import (
    DEFAULT_REVISION,
    build_hollow_cairn,
    build_newbie_graph_request,
    build_newbie_request,
    conditional_fact_count,
    connection_between,
    hidden_fact_count,
    scoped_counts,
    story_card,
    template_row_count,
)

TEMPLATE_SCOPE = "template"
HOLLOW_CAIRN_ALIAS_COUNT = 11
HIDDEN_FACT_LABEL = "F6.1"


async def _build(connection: AsyncConnection, request: TemplateBuildRequest):
    return await TemplateService(connection).build_template(request)


async def test_master_hollow_cairn_direct_write(db_connection: AsyncConnection) -> None:
    cairn = build_hollow_cairn()

    result = await _build(db_connection, cairn.request)

    assert result.is_created is True
    assert result.response.direct_status == "ready"
    assert result.response.enrichment_status == "not_needed"
    template_id = result.response.template_id
    counts = await scoped_counts(db_connection, template_id)
    assert counts["memory_entity"] == 7
    assert counts["memory_alias"] == HOLLOW_CAIRN_ALIAS_COUNT
    assert counts["memory_fact"] == 7
    assert counts["memory_fact_source"] == 7
    assert counts["memory_source"] == 14
    assert counts["memory_span"] == 14
    assert counts["memory_extraction_batch"] == 0
    assert counts["memory_embedding"] == 0
    assert await hidden_fact_count(db_connection, template_id) == 1
    assert await conditional_fact_count(db_connection, template_id) == 2


async def test_master_entities_are_authored_and_findable_by_alias(
    db_connection: AsyncConnection,
) -> None:
    cairn = build_hollow_cairn()
    result = await _build(db_connection, cairn.request)
    scopes = [(TEMPLATE_SCOPE, result.response.template_id)]

    rows = await entity_repo.get_entities_by_authored_ids(
        db_connection, scopes, list(cairn.ids.values())
    )
    matches = await entity_repo.find_entities_by_alias(
        db_connection, scopes, ["the scout"]
    )

    assert {row.authored_entity_id for row in rows} == set(cairn.ids.values())
    assert all(row.provenance == "authored" for row in rows)
    assert [(alias, row.canonical_name) for alias, row in matches] == [
        ("the scout", "Kestrel Vane")
    ]


async def test_hidden_fact_span_carries_flags_and_authored_id(
    db_connection: AsyncConnection,
) -> None:
    cairn = build_hollow_cairn()
    result = await _build(db_connection, cairn.request)
    hidden_fact = cairn.request.master.facts[5]

    spans = await span_repo.list_spans_by_labels(
        db_connection, TEMPLATE_SCOPE, result.response.template_id, [HIDDEN_FACT_LABEL]
    )

    assert len(spans) == 1
    assert spans[0].text == "The Warden vulnerable to Ember Sigil"
    assert spans[0].is_hidden is True
    assert spans[0].authored_fact_id == hidden_fact.fact_id
    assert set(spans[0].entity_ids) != set()


async def test_authored_fact_chain_link_is_stored_on_the_superseding_fact(
    db_connection: AsyncConnection,
) -> None:
    entity = TemplateEntityPayload(
        entity_id=uuid4(), entity_type="character", canonical_name="Mira"
    )
    old_fact = TemplateFactPayload(
        fact_id=uuid4(),
        subject_entity_id=entity.entity_id,
        predicate="rank",
        object_literal="squire",
    )
    new_fact = TemplateFactPayload(
        fact_id=uuid4(),
        subject_entity_id=entity.entity_id,
        predicate="rank",
        object_literal="knight",
        superseded_fact_id=old_fact.fact_id,
    )
    request = TemplateBuildRequest(
        scenario_id=uuid4(),
        publish_revision=DEFAULT_REVISION,
        mode="master",
        content_hash="hash",
        master=MasterTemplateContent(entities=[entity], facts=[old_fact, new_fact]),
    )

    result = await _build(db_connection, request)
    facts = await fact_repo.list_valid_facts_at(
        db_connection, uuid4(), result.response.template_id, 0
    )

    by_authored = {fact.authored_fact_id: fact for fact in facts}
    assert by_authored[new_fact.fact_id].supersedes_authored_fact_id == old_fact.fact_id
    assert by_authored[old_fact.fact_id].supersedes_authored_fact_id is None
    assert by_authored[new_fact.fact_id].object_literal == "knight"


async def test_map_connections_become_connects_to_facts(
    db_connection: AsyncConnection,
) -> None:
    cairn = build_hollow_cairn()
    connection = connection_between(
        cairn.ids["ashfall_village"], cairn.ids["hollow_cairn"], "mountain pass"
    )
    cairn.request.master.map_connections.append(connection)

    result = await _build(db_connection, cairn.request)
    spans = await span_repo.list_spans_by_labels(
        db_connection, TEMPLATE_SCOPE, result.response.template_id, ["F8.1"]
    )

    assert (
        spans[0].text == "Ashfall Village connects to The Hollow Cairn (mountain pass)"
    )
    assert spans[0].authored_fact_id == connection.connection_id
    assert (await scoped_counts(db_connection, result.response.template_id))[
        "memory_fact"
    ] == 8


async def test_newbie_cards_and_lore_are_searchable_immediately(
    db_connection: AsyncConnection,
) -> None:
    request = build_newbie_request(
        [
            story_card("c1", "Mira", "Character", "Mira guards the ferry at Ashfall."),
            story_card(
                "c2", "Red Guild", "Faction", "The Red Guild taxes every ferry."
            ),
            story_card("c3", "Ashfall", "Location", "A burned village by the river."),
        ],
        world_lore="Long ago the river changed course.\n\nThe ferrymen remember.",
    )

    result = await _build(db_connection, request)

    assert result.response.direct_status == "ready"
    assert result.response.enrichment_status == "pending"
    template_id = result.response.template_id
    counts = await scoped_counts(db_connection, template_id)
    assert counts["memory_entity"] == 3
    assert counts["memory_source"] == 4
    assert counts["memory_fact"] == 0
    hits = await span_repo.search_spans_bm25(
        db_connection, [(TEMPLATE_SCOPE, template_id)], "guards ferry", 5
    )
    assert hits
    assert hits[0][0].label == "C1.1"


async def test_newbie_card_spans_are_tagged_with_their_entities(
    db_connection: AsyncConnection,
) -> None:
    request = build_newbie_request(
        [story_card("c1", "Mira", "Character", "A quiet ferrywoman.")]
    )
    result = await _build(db_connection, request)
    scopes = [(TEMPLATE_SCOPE, result.response.template_id)]

    matches = await entity_repo.find_entities_by_alias(db_connection, scopes, ["mira"])
    spans = await span_repo.list_spans_by_labels(
        db_connection, TEMPLATE_SCOPE, result.response.template_id, ["C1.1"]
    )

    assert [row.entity_id for _alias, row in matches] == spans[0].entity_ids
    assert matches[0][1].entity_type == "character"


async def test_unknown_card_type_is_stored_as_other(
    db_connection: AsyncConnection,
) -> None:
    request = build_newbie_request([story_card("c1", "Fireball", "Spell", "Burns.")])
    result = await _build(db_connection, request)

    matches = await entity_repo.find_entities_by_alias(
        db_connection, [(TEMPLATE_SCOPE, result.response.template_id)], ["fireball"]
    )

    assert matches[0][1].entity_type == "other"


async def test_newbie_enrichment_is_pending_for_cards_only_and_not_needed_when_empty(
    db_connection: AsyncConnection,
) -> None:
    cards_only = build_newbie_request([story_card("c1", "Mira", "Character", "Hi.")])
    nothing = build_newbie_request([])

    cards_result = await _build(db_connection, cards_only)
    empty_result = await _build(db_connection, nothing)

    assert cards_result.response.enrichment_status == "pending"
    assert empty_result.response.enrichment_status == "not_needed"
    assert (await scoped_counts(db_connection, empty_result.response.template_id))[
        "memory_span"
    ] == 0


def _graph_entity(
    name: str,
    entity_type: str = "character",
    aliases: list[str] | None = None,
    description: str | None = None,
    is_player: bool = False,
) -> TemplateEntityPayload:
    return TemplateEntityPayload(
        entity_id=uuid4(),
        entity_type=entity_type,
        canonical_name=name,
        aliases=aliases or [],
        description=description,
        is_player=is_player,
    )


async def test_newbie_entities_and_facts_are_ingested_like_master(
    db_connection: AsyncConnection,
) -> None:
    mira = _graph_entity(
        "Mira", aliases=["the ferrywoman"], description="Mira guards the ferry."
    )
    hero = _graph_entity("Kai", is_player=True)
    ashfall = _graph_entity("Ashfall", "location", description="A burned village.")
    open_fact = TemplateFactPayload(
        fact_id=uuid4(),
        subject_entity_id=mira.entity_id,
        predicate="located_at",
        object_entity_id=ashfall.entity_id,
    )
    hidden_fact = TemplateFactPayload(
        fact_id=uuid4(),
        subject_entity_id=mira.entity_id,
        predicate="secret",
        object_literal="serves the guild",
        hidden=True,
    )
    request = build_newbie_graph_request(
        entities=[mira, hero, ashfall], facts=[open_fact, hidden_fact]
    )

    result = await _build(db_connection, request)

    template_id = result.response.template_id
    scopes = [(TEMPLATE_SCOPE, template_id)]
    rows = await entity_repo.get_entities_by_authored_ids(
        db_connection, scopes, [mira.entity_id, hero.entity_id, ashfall.entity_id]
    )
    by_authored = {row.authored_entity_id: row for row in rows}
    assert by_authored[mira.entity_id].canonical_name == "Mira"
    assert by_authored[ashfall.entity_id].entity_type == "location"
    assert by_authored[hero.entity_id].is_player is True
    assert by_authored[mira.entity_id].is_player is False
    matches = await entity_repo.find_entities_by_alias(
        db_connection, scopes, ["the ferrywoman"]
    )
    assert [row.authored_entity_id for _alias, row in matches] == [mira.entity_id]
    counts = await scoped_counts(db_connection, template_id)
    assert counts["memory_entity"] == 3
    assert counts["memory_fact"] == 2
    assert counts["memory_fact_source"] == 2
    assert await hidden_fact_count(db_connection, template_id) == 1
    assert result.response.enrichment_status == "pending"
    facts = await fact_repo.list_valid_facts_at(db_connection, uuid4(), template_id, 0)
    linked = {fact.authored_fact_id: fact for fact in facts}
    assert (
        linked[open_fact.fact_id].subject_entity_id
        == by_authored[mira.entity_id].entity_id
    )
    assert (
        linked[open_fact.fact_id].object_entity_id
        == by_authored[ashfall.entity_id].entity_id
    )
    assert linked[hidden_fact.fact_id].is_hidden is True


async def test_newbie_entity_descriptions_are_searchable_and_tagged(
    db_connection: AsyncConnection,
) -> None:
    mira = _graph_entity("Mira", description="Mira guards the ferry at Ashfall.")
    request = build_newbie_graph_request(
        entities=[mira], world_lore="The ferrywoman Mira is feared."
    )

    result = await _build(db_connection, request)

    template_id = result.response.template_id
    hits = await span_repo.search_spans_bm25(
        db_connection, [(TEMPLATE_SCOPE, template_id)], "guards ferry", 5
    )
    assert hits
    assert hits[0][0].label == "D1.1"
    rows = await entity_repo.get_entities_by_authored_ids(
        db_connection, [(TEMPLATE_SCOPE, template_id)], [mira.entity_id]
    )
    assert hits[0][0].entity_ids == [rows[0].entity_id]
    lore = await span_repo.list_spans_by_labels(
        db_connection, TEMPLATE_SCOPE, template_id, ["L1"]
    )
    assert lore[0].entity_ids == [rows[0].entity_id]


async def test_newbie_facts_only_template_needs_no_enrichment(
    db_connection: AsyncConnection,
) -> None:
    mira = _graph_entity("Mira")
    fact = TemplateFactPayload(
        fact_id=uuid4(),
        subject_entity_id=mira.entity_id,
        predicate="rank",
        object_literal="knight",
    )

    result = await _build(
        db_connection, build_newbie_graph_request(entities=[mira], facts=[fact])
    )

    assert result.response.enrichment_status == "not_needed"


async def test_newbie_entity_wins_over_card_with_the_same_derived_id_or_name(
    db_connection: AsyncConnection,
) -> None:
    scenario_id = uuid4()
    by_id = _graph_entity("Mira the Bold", description="Entity description.")
    by_id = by_id.model_copy(
        update={"entity_id": card_authored_entity_id(scenario_id, "c1")}
    )
    by_name = _graph_entity("Red Guild", "faction", description="Guild entity.")
    request = build_newbie_graph_request(
        scenario_id=scenario_id,
        cards=[
            story_card("c1", "Mira", "Character", "Card text one."),
            story_card("c2", "red guild", "Faction", "Card text two."),
            story_card("c3", "Ashfall", "Location", "Card only."),
        ],
        entities=[by_id, by_name],
    )

    result = await _build(db_connection, request)

    template_id = result.response.template_id
    counts = await scoped_counts(db_connection, template_id)
    assert counts["memory_entity"] == 3
    names = await _entity_names(db_connection, template_id)
    assert names == {"Mira the Bold", "Red Guild", "Ashfall"}
    refs = await _source_refs(db_connection, template_id)
    assert refs == {
        ("authored_description", str(by_id.entity_id)),
        ("authored_description", str(by_name.entity_id)),
        ("authored_card", "c3"),
    }


async def test_legacy_newbie_cards_only_template_is_unchanged(
    db_connection: AsyncConnection,
) -> None:
    scenario_id = uuid4()
    request = build_newbie_graph_request(
        scenario_id=scenario_id,
        cards=[story_card("c1", "Mira", "Character", "Mira guards the ferry.")],
    )

    result = await _build(db_connection, request)

    template_id = result.response.template_id
    rows = await entity_repo.get_entities_by_authored_ids(
        db_connection,
        [(TEMPLATE_SCOPE, template_id)],
        [card_authored_entity_id(scenario_id, "c1")],
    )
    assert len(rows) == 1
    assert await _source_refs(db_connection, template_id) == {("authored_card", "c1")}


async def test_newbie_replay_with_entities_is_a_no_op(
    db_connection: AsyncConnection,
) -> None:
    request = build_newbie_graph_request(entities=[_graph_entity("Mira")])

    first = await _build(db_connection, request)
    replay = await _build(db_connection, request)

    assert replay.is_created is False
    assert replay.response.template_id == first.response.template_id


async def test_newbie_unknown_fact_entity_is_rejected_before_any_write(
    db_connection: AsyncConnection,
) -> None:
    fact = TemplateFactPayload(
        fact_id=uuid4(),
        subject_entity_id=uuid4(),
        predicate="rank",
        object_literal="knight",
    )
    request = build_newbie_graph_request(facts=[fact])

    with pytest.raises(TemplateValidationError):
        await _build(db_connection, request)

    assert await template_row_count(db_connection, request.scenario_id) == 0


async def _entity_names(connection: AsyncConnection, template_id) -> set[str]:
    cursor = await connection.execute(
        "SELECT canonical_name FROM memory_entity "
        "WHERE scope_kind = 'template' AND scope_id = %s",
        (template_id,),
    )
    return {row[0] for row in await cursor.fetchall()}


async def _source_refs(
    connection: AsyncConnection, template_id
) -> set[tuple[str, str]]:
    cursor = await connection.execute(
        "SELECT source_kind, source_ref FROM memory_source "
        "WHERE scope_kind = 'template' AND scope_id = %s",
        (template_id,),
    )
    return {(row[0], row[1]) for row in await cursor.fetchall()}


async def test_empty_master_is_a_valid_template_with_no_rows(
    db_connection: AsyncConnection,
) -> None:
    request = build_hollow_cairn().request
    request.master = MasterTemplateContent()

    result = await _build(db_connection, request)

    assert result.is_created is True
    counts = await scoped_counts(db_connection, result.response.template_id)
    assert set(counts.values()) == {0}


async def test_identical_replay_is_a_no_op(db_connection: AsyncConnection) -> None:
    request = build_hollow_cairn().request
    first = await _build(db_connection, request)
    before = await scoped_counts(db_connection, first.response.template_id)

    second = await _build(db_connection, request)

    assert second.is_created is False
    assert second.response == first.response
    assert await scoped_counts(db_connection, first.response.template_id) == before


async def test_same_revision_with_different_hash_conflicts_and_writes_nothing(
    db_connection: AsyncConnection,
) -> None:
    request = build_hollow_cairn().request
    first = await _build(db_connection, request)
    before = await scoped_counts(db_connection, first.response.template_id)
    changed = request.model_copy(update={"content_hash": "another-hash"})

    with pytest.raises(TemplateContentConflictError) as caught:
        await _build(db_connection, changed)

    assert caught.value.status_code == 409
    assert caught.value.code == "template_content_conflict"
    assert await scoped_counts(db_connection, first.response.template_id) == before


async def test_invalid_content_writes_nothing(db_connection: AsyncConnection) -> None:
    request = build_hollow_cairn().request
    request.master.facts[0].subject_entity_id = uuid4()

    with pytest.raises(TemplateValidationError):
        await _build(db_connection, request)

    assert await template_row_count(db_connection, request.scenario_id) == 0


async def test_failure_midway_leaves_nothing_and_a_retry_succeeds(
    db_connection: AsyncConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = build_hollow_cairn().request

    async def fail_on_facts(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(template_service.fact_repo, "create_facts", fail_on_facts)
    with pytest.raises(RuntimeError):
        await _build(db_connection, request)
    monkeypatch.undo()

    assert await template_row_count(db_connection, request.scenario_id) == 0
    cursor = await db_connection.execute("SELECT count(*) FROM memory_entity")
    assert (await cursor.fetchone())[0] == 0
    retried = await _build(db_connection, request)
    assert retried.is_created is True


async def test_concurrent_identical_requests_create_one_template(
    db_connection: AsyncConnection, migrated_test_database_url: str
) -> None:
    request = build_hollow_cairn().request

    async with (
        await AsyncConnection.connect(migrated_test_database_url) as first,
        await AsyncConnection.connect(migrated_test_database_url) as second,
    ):
        results = await asyncio.gather(_build(first, request), _build(second, request))

    assert sorted(result.is_created for result in results) == [False, True]
    assert results[0].response.template_id == results[1].response.template_id
    counts = await scoped_counts(db_connection, results[0].response.template_id)
    assert counts["memory_entity"] == 7
    assert counts["memory_fact"] == 7
    assert await template_row_count(db_connection, request.scenario_id) == 1


async def test_two_revisions_of_one_scenario_never_share_rows(
    db_connection: AsyncConnection,
) -> None:
    scenario_id = uuid4()
    first = await _build(
        db_connection, build_hollow_cairn(scenario_id, 1, "hash-1").request
    )
    second = await _build(
        db_connection, build_hollow_cairn(scenario_id, 2, "hash-2").request
    )

    for result in (first, second):
        counts = await scoped_counts(db_connection, result.response.template_id)
        assert counts["memory_entity"] == 7
        scopes = [(TEMPLATE_SCOPE, result.response.template_id)]
        matches = await entity_repo.find_entities_by_alias(
            db_connection, scopes, ["kestrel"]
        )
        assert [row.scope_id for _alias, row in matches] == [
            result.response.template_id
        ]
    assert first.response.template_id != second.response.template_id


async def test_registration_resolves_a_built_template(
    db_connection: AsyncConnection,
) -> None:
    cairn = build_hollow_cairn()
    built = await _build(db_connection, cairn.request)
    playthrough_id = uuid4()
    registration = register_item(
        cairn.request.scenario_id, publish_revision=DEFAULT_REVISION
    )

    await IngestService(db_connection).ingest_items(
        build_request(playthrough_id, registration)
    )

    playthrough = await playthrough_repo.get_playthrough(db_connection, playthrough_id)
    assert playthrough is not None
    assert playthrough.template_id == built.response.template_id


async def test_authored_prose_never_reaches_logs(
    db_connection: AsyncConnection, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO")
    cairn = build_hollow_cairn()

    try:
        await _build(db_connection, cairn.request)
    finally:
        structlog.reset_defaults()

    captured = capsys.readouterr()
    assert "wandering scout" not in captured.out + captured.err
    assert "undying guardian" not in captured.out + captured.err
