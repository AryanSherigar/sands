"""Eligibility rules of memory-retrieval-engine.spec.md section 2, asserted against
every retrieval surface (exact, BM25, vector, graph) over one shared corpus."""

from uuid import UUID, uuid4

import pytest
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers
from tests.repositories.retrieval_corpus import (
    FACT_SURFACES,
    SPAN_SURFACES,
    Corpus,
    LabelSurface,
    build_corpus,
    put_fact,
    put_span,
)

span_surface = pytest.mark.parametrize(
    "surface", SPAN_SURFACES, ids=lambda fn: fn.__name__
)
fact_surface = pytest.mark.parametrize(
    "surface", FACT_SURFACES, ids=lambda fn: fn.__name__
)

WINDOW = 6
AT_SEQ = 30


async def visible(
    connection: AsyncConnection,
    surface: LabelSurface,
    corpus: Corpus,
    **context_options: object,
) -> set[str]:
    ctx = helpers.make_context(corpus.world, **context_options)  # type: ignore[arg-type]
    return await surface(connection, corpus, ctx)


# --- hidden / conditional: spans ---------------------------------------------


@span_surface
async def test_hidden_span_absent_until_its_authored_fact_is_revealed(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    secret_id = uuid4()
    await put_span(
        db_connection,
        corpus,
        corpus.world.template_scope,
        "secret",
        sequence=0,
        source_kind="authored_fact_text",
        is_hidden=True,
        authored_fact_id=secret_id,
    )

    unrevealed = await visible(db_connection, surface, corpus)
    other_revealed = await visible(db_connection, surface, corpus, revealed=[uuid4()])
    revealed = await visible(db_connection, surface, corpus, revealed=[secret_id])

    assert unrevealed == set()
    assert other_revealed == set()
    assert revealed == {"secret"}


@span_surface
async def test_hidden_span_without_authored_fact_id_is_never_returned(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    await put_span(
        db_connection,
        corpus,
        corpus.world.playthrough_scope,
        "orphan",
        is_hidden=True,
        sequence=1,
    )

    revealed_everything = await visible(
        db_connection, surface, corpus, revealed=[uuid4()], active=[uuid4()]
    )
    with_hidden_bypass = await visible(
        db_connection, surface, corpus, should_include_hidden=True
    )

    assert revealed_everything == set()
    assert with_hidden_bypass == set()


@span_surface
async def test_conditional_span_only_when_listed_active(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    rule_id = uuid4()
    await put_span(
        db_connection,
        corpus,
        corpus.world.template_scope,
        "rule",
        sequence=0,
        source_kind="authored_fact_text",
        conditional=True,
        authored_fact_id=rule_id,
    )
    await put_span(
        db_connection,
        corpus,
        corpus.world.playthrough_scope,
        "orphanrule",
        conditional=True,
        sequence=1,
    )

    inactive = await visible(db_connection, surface, corpus)
    revealed_only = await visible(db_connection, surface, corpus, revealed=[rule_id])
    active = await visible(db_connection, surface, corpus, active=[rule_id])

    assert inactive == set()
    assert revealed_only == set()
    assert active == {"rule"}


@span_surface
async def test_span_that_is_hidden_and_conditional_needs_both(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    both_id = uuid4()
    await put_span(
        db_connection,
        corpus,
        corpus.world.template_scope,
        "both",
        sequence=0,
        source_kind="authored_fact_text",
        is_hidden=True,
        conditional=True,
        authored_fact_id=both_id,
    )

    only_revealed = await visible(db_connection, surface, corpus, revealed=[both_id])
    only_active = await visible(db_connection, surface, corpus, active=[both_id])
    both = await visible(
        db_connection, surface, corpus, revealed=[both_id], active=[both_id]
    )

    assert only_revealed == set()
    assert only_active == set()
    assert both == {"both"}


@span_surface
async def test_span_include_hidden_bypasses_reveal_but_not_the_conditional_test(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    hidden_id, both_id, conditional_id = uuid4(), uuid4(), uuid4()
    scope = corpus.world.template_scope
    kind = "authored_fact_text"
    await put_span(
        db_connection, corpus, scope, "hidden", sequence=0, source_kind=kind,
        is_hidden=True, authored_fact_id=hidden_id,
    )  # fmt: skip
    await put_span(
        db_connection, corpus, scope, "both", sequence=0, source_kind=kind,
        is_hidden=True, conditional=True, authored_fact_id=both_id,
    )  # fmt: skip
    await put_span(
        db_connection, corpus, scope, "conditional", sequence=0, source_kind=kind,
        conditional=True, authored_fact_id=conditional_id,
    )  # fmt: skip

    bypass = await visible(db_connection, surface, corpus, should_include_hidden=True)
    bypass_active = await visible(
        db_connection, surface, corpus, should_include_hidden=True, active=[both_id]
    )

    assert bypass == {"hidden"}
    assert bypass_active == {"hidden", "both"}


# --- hidden / conditional: facts ---------------------------------------------


@fact_surface
async def test_hidden_fact_absent_until_revealed(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    secret_id = uuid4()
    await put_fact(
        db_connection,
        corpus,
        corpus.world.template_scope,
        "secret",
        is_hidden=True,
        authored_fact_id=secret_id,
    )

    assert await visible(db_connection, surface, corpus) == set()
    assert await visible(db_connection, surface, corpus, revealed=[uuid4()]) == set()
    revealed = await visible(db_connection, surface, corpus, revealed=[secret_id])
    assert revealed == {"secret"}


@fact_surface
async def test_hidden_fact_without_authored_fact_id_is_never_returned(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    await put_fact(
        db_connection, corpus, corpus.world.playthrough_scope, "orphan", is_hidden=True
    )

    listed = await visible(
        db_connection, surface, corpus, revealed=[uuid4()], active=[uuid4()]
    )
    bypass = await visible(db_connection, surface, corpus, should_include_hidden=True)

    assert listed == set()
    assert bypass == set()


@fact_surface
async def test_conditional_fact_only_when_listed_active(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    rule_id = uuid4()
    await put_fact(
        db_connection,
        corpus,
        corpus.world.template_scope,
        "rule",
        conditional=True,
        authored_fact_id=rule_id,
    )
    await put_fact(
        db_connection,
        corpus,
        corpus.world.playthrough_scope,
        "orphanrule",
        conditional=True,
    )

    assert await visible(db_connection, surface, corpus) == set()
    assert await visible(db_connection, surface, corpus, revealed=[rule_id]) == set()
    assert await visible(db_connection, surface, corpus, active=[rule_id]) == {"rule"}


@fact_surface
async def test_fact_that_is_hidden_and_conditional_needs_both(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    both_id = uuid4()
    await put_fact(
        db_connection,
        corpus,
        corpus.world.template_scope,
        "both",
        is_hidden=True,
        conditional=True,
        authored_fact_id=both_id,
    )

    assert await visible(db_connection, surface, corpus, revealed=[both_id]) == set()
    assert await visible(db_connection, surface, corpus, active=[both_id]) == set()
    both = await visible(
        db_connection, surface, corpus, revealed=[both_id], active=[both_id]
    )
    assert both == {"both"}


@fact_surface
async def test_fact_include_hidden_bypasses_reveal_but_not_the_conditional_test(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    hidden_id, both_id, conditional_id = uuid4(), uuid4(), uuid4()
    scope = corpus.world.template_scope
    await put_fact(
        db_connection, corpus, scope, "hidden", is_hidden=True,
        authored_fact_id=hidden_id,
    )  # fmt: skip
    await put_fact(
        db_connection, corpus, scope, "both", is_hidden=True, conditional=True,
        authored_fact_id=both_id,
    )  # fmt: skip
    await put_fact(
        db_connection, corpus, scope, "conditional", conditional=True,
        authored_fact_id=conditional_id,
    )  # fmt: skip

    bypass = await visible(db_connection, surface, corpus, should_include_hidden=True)
    bypass_active = await visible(
        db_connection, surface, corpus, should_include_hidden=True, active=[both_id]
    )

    assert bypass == {"hidden"}
    assert bypass_active == {"hidden", "both"}


# --- validity and supersession -----------------------------------------------


@fact_surface
async def test_fact_superseded_at_20_is_absent_at_25_and_present_at_15(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    fact_id = await put_fact(
        db_connection, corpus, world.playthrough_scope, "moved", valid_from_seq=3
    )
    await helpers.supersede_fact(db_connection, world.playthrough_id, fact_id, 20)

    assert await visible(db_connection, surface, corpus, at_seq=15) == {"moved"}
    assert await visible(db_connection, surface, corpus, at_seq=19) == {"moved"}
    assert await visible(db_connection, surface, corpus, at_seq=20) == set()
    assert await visible(db_connection, surface, corpus, at_seq=25) == set()


@fact_surface
async def test_fact_is_absent_before_its_valid_from_seq(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    await put_fact(
        db_connection,
        corpus,
        corpus.world.playthrough_scope,
        "future",
        valid_from_seq=20,
    )

    assert await visible(db_connection, surface, corpus, at_seq=19) == set()
    assert await visible(db_connection, surface, corpus, at_seq=20) == {"future"}


@fact_surface
async def test_template_fact_superseded_in_one_playthrough_stays_valid_in_a_sibling(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    fact_id = await put_fact(db_connection, corpus, world.template_scope, "lore")
    await helpers.supersede_fact(db_connection, world.playthrough_id, fact_id, 10)
    sibling_ctx = helpers.make_context(world)
    sibling_ctx = sibling_ctx.model_copy(
        update={"playthrough_id": world.sibling_playthrough_id}
    )

    in_a = await visible(db_connection, surface, corpus, at_seq=20)
    in_b = await surface(db_connection, corpus, sibling_ctx)

    assert in_a == set()
    assert in_b == {"lore"}


# --- authored supersession chain ---------------------------------------------


async def _put_chain(
    connection: AsyncConnection,
    corpus: Corpus,
    *,
    is_c_hidden: bool = False,
    is_c_conditional: bool = False,
) -> tuple[UUID, UUID, UUID]:
    scope = corpus.world.template_scope
    a_id, b_id, c_id = uuid4(), uuid4(), uuid4()
    await put_fact(connection, corpus, scope, "a", authored_fact_id=a_id)
    await put_fact(
        connection, corpus, scope, "b",
        authored_fact_id=b_id, supersedes_authored_fact_id=a_id,
    )  # fmt: skip
    await put_fact(
        connection, corpus, scope, "c",
        authored_fact_id=c_id, supersedes_authored_fact_id=b_id,
        is_hidden=is_c_hidden, conditional=is_c_conditional,
    )  # fmt: skip
    return a_id, b_id, c_id


@fact_surface
async def test_authored_chain_shows_only_the_latest_eligible_link(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    await _put_chain(db_connection, corpus)

    assert await visible(db_connection, surface, corpus) == {"c"}


@fact_surface
async def test_authored_chain_with_hidden_unrevealed_tail_keeps_the_middle_link(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    _a, _b, c_id = await _put_chain(db_connection, corpus, is_c_hidden=True)

    assert await visible(db_connection, surface, corpus) == {"b"}
    assert await visible(db_connection, surface, corpus, revealed=[c_id]) == {"c"}


@fact_surface
async def test_authored_chain_with_inactive_conditional_tail_keeps_the_middle_link(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    _a, _b, c_id = await _put_chain(db_connection, corpus, is_c_conditional=True)

    assert await visible(db_connection, surface, corpus) == {"b"}
    assert await visible(db_connection, surface, corpus, active=[c_id]) == {"c"}


@fact_surface
async def test_authored_chain_tail_does_not_supersede_when_it_is_not_yet_valid(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    scope = corpus.world.template_scope
    old_id, new_id = uuid4(), uuid4()
    await put_fact(db_connection, corpus, scope, "old", authored_fact_id=old_id)
    await put_fact(
        db_connection, corpus, scope, "new", valid_from_seq=25,
        authored_fact_id=new_id, supersedes_authored_fact_id=old_id,
    )  # fmt: skip

    assert await visible(db_connection, surface, corpus, at_seq=24) == {"old"}
    assert await visible(db_connection, surface, corpus, at_seq=25) == {"new"}


@fact_surface
async def test_authored_successor_superseded_in_this_playthrough_no_longer_supersedes(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    scope = corpus.world.template_scope
    old_id, new_id = uuid4(), uuid4()
    await put_fact(db_connection, corpus, scope, "old", authored_fact_id=old_id)
    new_fact_id = await put_fact(
        db_connection, corpus, scope, "new",
        authored_fact_id=new_id, supersedes_authored_fact_id=old_id,
    )  # fmt: skip
    await helpers.supersede_fact(
        db_connection, corpus.world.playthrough_id, new_fact_id, 10
    )

    assert await visible(db_connection, surface, corpus) == {"old"}


@fact_surface
async def test_authored_supersession_in_another_template_has_no_effect(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    old_id = uuid4()
    await put_fact(
        db_connection, corpus, world.template_scope, "old", authored_fact_id=old_id
    )
    await put_fact(
        db_connection,
        corpus,
        world.other_template_scope,
        "foreign_new",
        authored_fact_id=uuid4(),
        supersedes_authored_fact_id=old_id,
    )

    assert await visible(db_connection, surface, corpus) == {"old"}


@span_surface
async def test_span_of_a_superseded_authored_fact_is_absent(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    scope = corpus.world.template_scope
    old_id, new_id = uuid4(), uuid4()
    kind = "authored_fact_text"
    await put_span(
        db_connection, corpus, scope, "oldtext", sequence=0, source_kind=kind,
        authored_fact_id=old_id,
    )  # fmt: skip
    await put_fact(
        db_connection, corpus, scope, "new", is_hidden=True,
        authored_fact_id=new_id, supersedes_authored_fact_id=old_id,
    )  # fmt: skip

    assert await visible(db_connection, surface, corpus) == {"oldtext"}
    assert await visible(db_connection, surface, corpus, revealed=[new_id]) == set()


# --- recent window -----------------------------------------------------------


@span_surface
async def test_turn_spans_inside_the_window_are_excluded_and_the_boundary_is_kept(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    scope = corpus.world.playthrough_scope
    boundary = AT_SEQ - WINDOW
    await put_span(db_connection, corpus, scope, "inside", sequence=boundary + 1)
    await put_span(db_connection, corpus, scope, "atboundary", sequence=boundary)
    await put_span(db_connection, corpus, scope, "older", sequence=boundary - 5)
    await put_span(
        db_connection, corpus, scope, "actioninside",
        sequence=AT_SEQ, source_kind="turn_action",
    )  # fmt: skip
    await put_span(
        db_connection, corpus, scope, "actionold",
        sequence=boundary, source_kind="turn_action",
    )  # fmt: skip

    result = await visible(db_connection, surface, corpus)

    assert result == {"atboundary", "older", "actionold"}


@span_surface
async def test_setup_and_authored_spans_are_kept_when_at_seq_is_below_the_window(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    await put_span(
        db_connection, corpus, world.playthrough_scope, "setup",
        sequence=0, source_kind="setup",
    )  # fmt: skip
    await put_span(
        db_connection, corpus, world.template_scope, "lore",
        sequence=0, source_kind="authored_lore",
    )  # fmt: skip
    await put_span(db_connection, corpus, world.playthrough_scope, "turn", sequence=0)

    result = await visible(db_connection, surface, corpus, at_seq=2)

    assert result == {"setup", "lore"}


@span_surface
async def test_template_spans_are_never_window_excluded(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    await put_span(
        db_connection, corpus, corpus.world.template_scope, "lore",
        sequence=AT_SEQ, source_kind="authored_card",
    )  # fmt: skip

    assert await visible(db_connection, surface, corpus, window=100) == {"lore"}


# --- scope -------------------------------------------------------------------


@span_surface
async def test_spans_of_other_playthroughs_and_templates_never_leak(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    await put_span(db_connection, corpus, world.playthrough_scope, "mine")
    await put_span(db_connection, corpus, world.template_scope, "lore", sequence=0)
    await put_span(db_connection, corpus, world.sibling_scope, "sibling")
    await put_span(db_connection, corpus, world.foreign_scope, "foreign")
    await put_span(
        db_connection, corpus, world.other_template_scope, "foreignlore", sequence=0
    )

    assert await visible(db_connection, surface, corpus) == {"mine", "lore"}


@span_surface
async def test_null_template_reads_playthrough_scope_only_for_spans(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    await put_span(db_connection, corpus, world.playthrough_scope, "mine")
    await put_span(db_connection, corpus, world.template_scope, "lore", sequence=0)
    await put_span(
        db_connection, corpus, world.other_template_scope, "foreignlore", sequence=0
    )

    result = await visible(db_connection, surface, corpus, has_template=False)

    assert result == {"mine"}


@fact_surface
async def test_facts_of_other_playthroughs_and_templates_never_leak(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    await put_fact(db_connection, corpus, world.playthrough_scope, "mine")
    await put_fact(db_connection, corpus, world.template_scope, "lore")
    await put_fact(db_connection, corpus, world.sibling_scope, "sibling")
    await put_fact(db_connection, corpus, world.foreign_scope, "foreign")
    await put_fact(db_connection, corpus, world.other_template_scope, "foreignlore")

    assert await visible(db_connection, surface, corpus) == {"mine", "lore"}


@fact_surface
async def test_null_template_reads_playthrough_scope_only_for_facts(
    db_connection: AsyncConnection, surface: LabelSurface
) -> None:
    corpus = await build_corpus(db_connection)
    world = corpus.world
    await put_fact(db_connection, corpus, world.playthrough_scope, "mine")
    await put_fact(db_connection, corpus, world.template_scope, "lore")

    assert await visible(db_connection, surface, corpus, has_template=False) == {"mine"}
