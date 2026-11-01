"""Rendering, budget fitting and grouping of retrieval items. Pure."""

import random
from datetime import UTC, datetime
from fractions import Fraction
from uuid import UUID, uuid4

from app.models.evidence import SpanRow
from app.models.facts import (
    CommitmentRow,
    CommitmentStatusRow,
    FactRow,
)
from app.models.retrieval_rows import SpanOrigin
from app.models.retrieve import MemoryItem
from app.services.fusion import Candidate, FusedCandidate
from app.services.packing import (
    PackBudget,
    RenderContext,
    build_memory_item,
    build_ranked_items,
    estimate_tokens,
    pack_items,
    render_commitment,
    render_fact,
)
from app.services.retrieval_types import CandidatePool, CommitmentRecord

CHARS_PER_TOKEN = 3
SHARE = 0.4


def make_span(
    *, sequence: int = 1, text: str = "the text", label: str = "S1", entities=()
) -> SpanRow:
    return SpanRow(
        span_id=uuid4(),
        source_id=uuid4(),
        scope_kind="playthrough",
        scope_id=uuid4(),
        sequence=sequence,
        ordinal=0,
        start_offset=0,
        end_offset=len(text),
        text=text,
        token_count=1,
        label=label,
        entity_ids=list(entities),
    )


def make_fact(
    subject: UUID,
    *,
    predicate: str = "owns",
    object_entity_id: UUID | None = None,
    object_literal: str | None = None,
    assertion: str = "occurred",
    speaker: UUID | None = None,
    authority: str = "extracted",
    valid_from_seq: int = 3,
) -> FactRow:
    return FactRow(
        fact_id=uuid4(),
        created_at=datetime.now(UTC),
        scope_kind="playthrough",
        scope_id=uuid4(),
        subject_entity_id=subject,
        predicate=predicate,
        object_entity_id=object_entity_id,
        object_literal=object_literal,
        authority=authority,
        assertion=assertion,
        speaker_entity_id=speaker,
        valid_from_seq=valid_from_seq,
    )


def make_commitment(
    owner: UUID,
    *,
    kind: str = "promise",
    counterparty: UUID | None = None,
    summary: str = "to bring the key",
    opened_seq: int = 4,
) -> CommitmentRow:
    return CommitmentRow(
        commitment_id=uuid4(),
        playthrough_id=uuid4(),
        kind=kind,
        owner_entity_id=owner,
        counterparty_entity_id=counterparty,
        summary=summary,
        opened_seq=opened_seq,
        opening_span_id=uuid4(),
        extraction_batch_id=uuid4(),
    )


def make_status(
    commitment: CommitmentRow,
    *,
    at_seq: int,
    status: str,
    evidence_span_id: UUID | None = None,
) -> CommitmentStatusRow:
    return CommitmentStatusRow(
        commitment_id=commitment.commitment_id,
        at_seq=at_seq,
        status=status,
        evidence_span_id=evidence_span_id,
    )


def make_context(
    *,
    names: dict[UUID, str] | None = None,
    participants: dict[UUID, str] | None = None,
    origins: dict[UUID, SpanOrigin] | None = None,
    labels: dict[UUID, str] | None = None,
) -> RenderContext:
    return RenderContext(
        entity_names=names or {},
        participant_names=participants or {},
        span_origins=origins or {},
        evidence_labels=labels or {},
    )


def fused_of(candidate: Candidate, *branches: str) -> FusedCandidate:
    ranks = {branch: 1 for branch in branches}
    return FusedCandidate(candidate, Fraction(1, 61), ranks)  # type: ignore[arg-type]


def item(
    text: str,
    *,
    branches: list[str] | None = None,
    sequence: int = 1,
    entity_ids: list[UUID] | None = None,
    item_id: UUID | None = None,
) -> MemoryItem:
    return MemoryItem(
        kind="span",
        item_id=item_id or uuid4(),
        source_kind="turn_narration",
        authority="accepted",
        assertion=None,
        sequence=sequence,
        speaker=None,
        text=text,
        entity_ids=entity_ids or [],
        branches=branches or ["bm25"],  # type: ignore[arg-type]
    )


def budget(tokens: int, *, should_limit: bool = True) -> PackBudget:
    return PackBudget(
        budget_tokens=tokens,
        chars_per_token=CHARS_PER_TOKEN,
        graph_and_exact_only_share=SHARE,
        should_limit_graph_and_exact_only=should_limit,
    )


def text_of_tokens(tokens: int) -> str:
    return "x" * (tokens * CHARS_PER_TOKEN)


def test_token_estimate_rounds_up() -> None:
    assert estimate_tokens("", 3) == 0
    assert estimate_tokens("a", 3) == 1
    assert estimate_tokens("abc", 3) == 1
    assert estimate_tokens("abcd", 3) == 2


def test_fact_renders_subject_predicate_object_with_entity_names() -> None:
    subject, target = uuid4(), uuid4()
    fact = make_fact(subject, predicate="guards_the", object_entity_id=target)

    text = render_fact(fact, make_context(names={subject: "Mara", target: "Gate"}))

    assert text == "Mara guards the Gate"


def test_fact_renders_a_literal_object() -> None:
    subject = uuid4()
    fact = make_fact(subject, predicate="has_hair", object_literal="red")

    assert (
        render_fact(fact, make_context(names={subject: "Mara"})) == "Mara has hair red"
    )


def test_claimed_by_suffix_only_for_stated_attempted_believed_with_a_speaker() -> None:
    subject, speaker = uuid4(), uuid4()
    context = make_context(names={subject: "Mara", speaker: "Orin"})

    def render(assertion: str, speaker_id: UUID | None) -> str:
        fact = make_fact(
            subject, object_literal="a thief", assertion=assertion, speaker=speaker_id
        )
        return render_fact(fact, context)

    assert render("stated", speaker).endswith(" (claimed by Orin)")
    assert render("attempted", speaker).endswith(" (claimed by Orin)")
    assert render("believed", speaker).endswith(" (claimed by Orin)")
    assert "claimed" not in render("occurred", speaker)
    assert "claimed" not in render("stated", None)
    assert "claimed" not in render("stated", uuid4())


def render_commitment_text(
    kind: str = "promise",
    *,
    with_counterparty: bool = True,
    status: tuple[int, str, UUID | None] | None = None,
    labels: dict[UUID, str] | None = None,
) -> str:
    owner, other = uuid4(), uuid4()
    commitment = make_commitment(
        owner,
        kind=kind,
        counterparty=other if with_counterparty else None,
        summary="the sword",
        opened_seq=4,
    )
    status_row = None
    if status is not None:
        status_row = make_status(
            commitment, at_seq=status[0], status=status[1], evidence_span_id=status[2]
        )
    context = make_context(names={owner: "Mara", other: "Orin"}, labels=labels)
    return render_commitment(CommitmentRecord(commitment, status_row), context)


def test_commitment_verb_map() -> None:
    assert render_commitment_text("promise").startswith("Mara promised Orin: ")
    assert render_commitment_text("debt").startswith("Mara owes Orin: ")
    assert render_commitment_text("quest").startswith("Mara assigned Orin: ")
    assert render_commitment_text("threat").startswith("Mara threatened Orin: ")


def test_commitment_without_counterparty_omits_it() -> None:
    text = render_commitment_text("promise", with_counterparty=False)

    assert text == "Mara promised: the sword — open (turn 4)"


def test_commitment_without_status_is_open_at_its_opening_turn() -> None:
    assert render_commitment_text() == "Mara promised Orin: the sword — open (turn 4)"


def test_commitment_shows_the_latest_status_and_its_turn() -> None:
    text = render_commitment_text(status=(12, "fulfilled", None))

    assert text == "Mara promised Orin: the sword — fulfilled (turn 12)"


def test_commitment_label_appended_only_when_the_evidence_span_is_eligible() -> None:
    evidence = uuid4()

    with_label = render_commitment_text(
        status=(12, "fulfilled", evidence), labels={evidence: "S12"}
    )
    without_label = render_commitment_text(
        status=(12, "fulfilled", evidence), labels={}
    )
    unrelated_label = render_commitment_text(
        status=(12, "fulfilled", evidence), labels={uuid4(): "S99"}
    )

    assert with_label.endswith("fulfilled (turn 12) [S12]")
    assert without_label.endswith("fulfilled (turn 12)")
    assert unrelated_label.endswith("fulfilled (turn 12)")


def test_span_item_authority_source_kind_and_speaker() -> None:
    participant = uuid4()
    span = make_span(text="verbatim  text", entities=[uuid4()])
    origin = SpanOrigin(source_kind="authored_lore", actor_participant_id=participant)
    context = make_context(
        origins={span.span_id: origin}, participants={participant: "Aria"}
    )
    pool = CandidatePool()
    fused = fused_of(pool.add_span(span), "bm25", "vector")

    built = build_memory_item(fused, pool, context)

    assert built is not None
    assert built.text == "verbatim  text"
    assert built.authority == "authored"
    assert built.source_kind == "authored_lore"
    assert built.speaker == "Aria"
    assert built.assertion is None
    assert built.entity_ids == span.entity_ids
    assert built.branches == ["bm25", "vector"]


def test_span_authority_is_accepted_for_turn_and_setup_sources() -> None:
    for kind in ("turn_action", "turn_narration", "setup"):
        span = make_span()
        origin = SpanOrigin(source_kind=kind, actor_participant_id=None)
        pool = CandidatePool()
        fused = fused_of(pool.add_span(span), "bm25")

        built = build_memory_item(
            fused, pool, make_context(origins={span.span_id: origin})
        )

        assert built is not None
        assert built.authority == "accepted"
        assert built.speaker is None


def test_span_speaker_is_none_for_an_unknown_participant() -> None:
    span = make_span()
    origin = SpanOrigin(source_kind="turn_action", actor_participant_id=uuid4())
    pool = CandidatePool()
    fused = fused_of(pool.add_span(span), "bm25")

    built = build_memory_item(
        fused, pool, make_context(origins={span.span_id: origin}, participants={})
    )

    assert built is not None
    assert built.speaker is None


def test_a_span_without_a_resolved_origin_is_dropped() -> None:
    span = make_span()
    pool = CandidatePool()
    fused = fused_of(pool.add_span(span), "bm25")

    assert build_memory_item(fused, pool, make_context()) is None
    assert build_ranked_items([fused], pool, make_context()) == []


def test_fact_item_fields() -> None:
    subject, target, speaker = uuid4(), uuid4(), uuid4()
    fact = make_fact(
        subject,
        object_entity_id=target,
        assertion="believed",
        speaker=speaker,
        authority="authored",
        valid_from_seq=9,
    )
    pool = CandidatePool()
    fused = fused_of(pool.add_fact(fact), "graph")
    context = make_context(names={subject: "Mara", target: "Gate", speaker: "Orin"})

    built = build_memory_item(fused, pool, context)

    assert built is not None
    assert (built.kind, built.item_id, built.sequence) == ("fact", fact.fact_id, 9)
    assert built.authority == "authored"
    assert built.assertion == "believed"
    assert built.speaker == "Orin"
    assert built.entity_ids == [subject, target]
    assert built.branches == ["graph"]


def test_fact_speaker_is_none_without_a_speaker_entity() -> None:
    subject = uuid4()
    pool = CandidatePool()
    fused = fused_of(pool.add_fact(make_fact(subject, object_literal="x")), "exact")

    built = build_memory_item(fused, pool, make_context(names={subject: "Mara"}))

    assert built is not None
    assert built.speaker is None
    assert built.entity_ids == [subject]


def test_commitment_item_fields() -> None:
    owner, other = uuid4(), uuid4()
    commitment = make_commitment(owner, counterparty=other)
    status = make_status(commitment, at_seq=15, status="broken")
    pool = CandidatePool()
    fused = fused_of(pool.add_commitment(CommitmentRecord(commitment, status)), "exact")

    built = build_memory_item(fused, pool, make_context(names={owner: "A", other: "B"}))

    assert built is not None
    assert built.kind == "commitment"
    assert built.authority == "extracted"
    assert built.assertion is None
    assert built.speaker is None
    assert built.sequence == 15
    assert built.entity_ids == [owner, other]


def test_never_over_budget_and_never_a_partial_item_across_many_budgets() -> None:
    rng = random.Random(7)
    items = [
        item(
            f"item-{index}-" + "y" * rng.randint(0, 60),
            branches=rng.choice(
                [["exact"], ["graph"], ["exact", "graph"], ["bm25"], ["bm25", "exact"]]
            ),
            sequence=index,
        )
        for index in range(60)
    ]
    original_texts = {each.text for each in items}

    for budget_tokens in range(1, 120):
        result = pack_items(items, [], budget(budget_tokens))

        used = sum(estimate_tokens(each.text, CHARS_PER_TOKEN) for each in result.items)
        assert used == result.token_count
        assert used <= budget_tokens
        assert {each.text for each in result.items} <= original_texts


def test_an_item_that_does_not_fit_is_skipped_and_the_next_is_tried() -> None:
    big, small_one, small_two = (
        item(text_of_tokens(50)),
        item(text_of_tokens(2), sequence=1),
        item(text_of_tokens(3), sequence=2),
    )

    result = pack_items([big, small_one, small_two], [], budget(6))

    assert [each.text for each in result.items] == [small_one.text, small_two.text]
    assert result.is_truncated is True


def test_refill_after_a_skip_takes_a_later_smaller_item() -> None:
    first, second, third = (
        item(text_of_tokens(4), sequence=1),
        item(text_of_tokens(4), sequence=2),
        item(text_of_tokens(1), sequence=3),
    )

    result = pack_items([first, second, third], [], budget(5))

    assert {each.item_id for each in result.items} == {first.item_id, third.item_id}
    assert result.token_count == 5


def test_not_truncated_when_everything_fits() -> None:
    result = pack_items(
        [item(text_of_tokens(2)), item(text_of_tokens(2))], [], budget(4)
    )

    assert result.is_truncated is False
    assert len(result.items) == 2


def test_exact_and_graph_only_items_share_at_most_forty_percent() -> None:
    restricted = [
        item(text_of_tokens(10), branches=["exact"], sequence=n) for n in range(6)
    ]
    restricted += [
        item(text_of_tokens(10), branches=["graph"], sequence=10 + n) for n in range(6)
    ]

    result = pack_items(restricted, [], budget(100))

    assert result.token_count == 40
    assert len(result.items) == 4


def test_share_cap_leaves_room_for_lexical_and_semantic_items() -> None:
    ranked = [
        item(text_of_tokens(10), branches=["exact"], sequence=n) for n in range(10)
    ]
    ranked += [
        item(text_of_tokens(10), branches=["bm25"], sequence=20 + n) for n in range(10)
    ]

    result = pack_items(ranked, [], budget(100))

    exact_tokens = sum(10 for each in result.items if each.branches == ["exact"])
    assert exact_tokens <= 40
    assert result.token_count == 100


def test_an_item_found_by_exact_and_a_lexical_branch_is_not_restricted() -> None:
    ranked = [
        item(text_of_tokens(10), branches=["exact", "bm25"], sequence=n)
        for n in range(10)
    ]

    assert pack_items(ranked, [], budget(100)).token_count == 100


def test_share_limit_can_be_lifted_for_the_extraction_context() -> None:
    ranked = [
        item(text_of_tokens(10), branches=["exact"], sequence=n) for n in range(10)
    ]

    result = pack_items(ranked, [], budget(100, should_limit=False))

    assert result.token_count == 100


def test_identical_text_from_different_sources_stays_as_two_items() -> None:
    first = item("same words", sequence=1)
    second = item("same words", sequence=2)

    result = pack_items([first, second], [], budget(50))

    assert [each.item_id for each in result.items] == [first.item_id, second.item_id]


def test_group_order_follows_best_fused_rank_and_items_are_chronological() -> None:
    seed_a, seed_b = uuid4(), uuid4()
    a_late = item("a late", sequence=9, entity_ids=[seed_a])
    b_best = item("b best", sequence=5, entity_ids=[seed_b])
    a_early = item("a early", sequence=2, entity_ids=[seed_a])

    result = pack_items([b_best, a_late, a_early], [seed_a, seed_b], budget(100))

    assert [each.text for each in result.items] == ["b best", "a early", "a late"]


def test_primary_entity_is_the_first_seed_else_the_first_entity() -> None:
    seed, other, stranger = uuid4(), uuid4(), uuid4()
    with_seed = item("with seed", sequence=3, entity_ids=[other, seed])
    seed_group_mate = item("seed mate", sequence=1, entity_ids=[seed])
    non_seed = item("non seed", sequence=2, entity_ids=[stranger, other])
    ranked = [non_seed, with_seed, seed_group_mate]

    result = pack_items(ranked, [seed], budget(100))

    assert [each.text for each in result.items] == [
        "non seed",
        "seed mate",
        "with seed",
    ]


def test_items_without_entities_form_a_trailing_group() -> None:
    seed = uuid4()
    lonely = item("no entity", sequence=1)
    anchored = item("anchored", sequence=8, entity_ids=[seed])

    result = pack_items([lonely, anchored], [seed], budget(100))

    assert [each.text for each in result.items] == ["anchored", "no entity"]


def test_equal_sequence_falls_back_to_id_order() -> None:
    low = item("low", sequence=1, item_id=UUID(int=1))
    high = item("high", sequence=1, item_id=UUID(int=2))

    result = pack_items([high, low], [], budget(100))

    assert [each.text for each in result.items] == ["low", "high"]


def test_empty_input_gives_an_empty_untruncated_result() -> None:
    result = pack_items([], [], budget(10))

    assert (result.items, result.token_count, result.is_truncated) == ([], 0, False)
