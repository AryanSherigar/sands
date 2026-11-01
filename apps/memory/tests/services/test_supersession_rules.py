"""Pure supersession rules: candidate selection, tiers, judge output validation."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models.extraction import (
    ExtractedFact,
    SupersessionClaim,
    SupersessionJudgement,
    SupersessionJudgeOutput,
)
from app.models.facts import FactRow
from app.services.supersession_rules import (
    DROP_JUDGE_BAD_INDEX,
    DROP_JUDGE_UNOFFERED_ID,
    REASON_FUNCTIONAL,
    CandidateContext,
    FactCandidates,
    merge_claims,
    render_judge_input,
    select_candidates,
    split_by_tier,
    validate_judgements,
)

SUBJECT = uuid4()
CAP = 5


def _row(
    predicate: str = "located_in",
    literal: str | None = "the Wet Rope inn",
    *,
    object_entity_id: UUID | None = None,
    authority: str = "extracted",
    assertion: str = "occurred",
    valid_from_seq: int = 3,
) -> FactRow:
    return FactRow(
        fact_id=uuid4(),
        created_at=datetime.now(UTC),
        scope_kind="playthrough",
        scope_id=uuid4(),
        subject_entity_id=SUBJECT,
        predicate=predicate,
        object_entity_id=object_entity_id,
        object_literal=literal,
        authority=authority,  # type: ignore[arg-type]
        assertion=assertion,  # type: ignore[arg-type]
        valid_from_seq=valid_from_seq,
    )


def _fact(
    predicate: str = "located_in",
    literal: str | None = "the Brasswrights attic",
    object_ref: str | None = None,
) -> ExtractedFact:
    return ExtractedFact(
        subject=str(SUBJECT),
        predicate=predicate,
        object=object_ref,
        object_literal=literal,
        assertion="occurred",
        speaker=None,
        evidence=["S9.1"],
    )


def _pair(fact: ExtractedFact, *rows: FactRow, index: int = 0) -> FactCandidates:
    return FactCandidates(index, fact, SUBJECT, tuple(rows))


def _ctx(
    *rows: FactRow, refs: dict[str, str] | None = None, cap: int = CAP
) -> CandidateContext:
    names = {str(SUBJECT): "Pip"}
    return CandidateContext(refs or {}, names, tuple(rows), cap)


def _select(
    fact: ExtractedFact, *rows: FactRow, cap: int = CAP, refs=None
) -> tuple[FactRow, ...]:
    return select_candidates(fact, SUBJECT, _ctx(*rows, refs=refs, cap=cap))


def test_a_changed_value_with_the_same_predicate_is_a_candidate() -> None:
    old = _row()

    assert _select(_fact(), old) == (old,)


def test_a_restated_value_is_not_a_candidate() -> None:
    same = _row(literal="The Brasswrights  attic")

    assert _select(_fact(), same) == ()


def test_game_managed_and_non_occurred_facts_are_never_candidates() -> None:
    accepted = _row(authority="accepted")
    claimed = _row(assertion="stated")

    assert _select(_fact(), accepted, claimed) == ()


def test_a_different_predicate_is_a_candidate_when_the_object_overlaps() -> None:
    overlapping = _row("lodges_at", "the old Wet Rope inn")
    fact = _fact("located_in", "the Wet Rope inn cellar")

    assert _select(fact, overlapping, *[_row("carries", "a lamp")] * 9) == (
        overlapping,
    )


def test_a_subject_with_few_facts_offers_all_of_them() -> None:
    unrelated = _row("carries", "a copper lantern")

    assert _select(_fact("wants", "brass lamp"), unrelated) == (unrelated,)


def test_a_busy_subject_offers_only_matching_facts() -> None:
    busy = [_row("notes_detail", f"minor detail {n}") for n in range(12)]
    match = _row("keeps", "the star charts in the vault")
    fact = ExtractedFact(
        subject="charts-key",
        predicate="located_in",
        object=None,
        object_literal="the glass loft",
        assertion="occurred",
        speaker=None,
        evidence=["S9.1"],
    )
    ctx = CandidateContext(
        {}, {str(SUBJECT): "Pip", "charts-key": "star charts"}, (*busy, match), CAP
    )

    assert select_candidates(fact, uuid4(), ctx) == (match,)


def test_a_holder_change_finds_the_old_fact_of_another_subject() -> None:
    other = uuid4()
    old = _row("keeps", "the reliquary key in her sleeve")
    fact = ExtractedFact(
        subject=str(other),
        predicate="holds",
        object=None,
        object_literal="an iron key",
        assertion="occurred",
        speaker=None,
        evidence=["S9.1"],
    )
    ctx = CandidateContext({}, {str(other): "Brother Cael"}, (old,), CAP)

    assert select_candidates(fact, other, ctx) == (old,)


def test_same_predicate_ranks_first_then_overlap_then_newest_and_is_capped() -> None:
    other = _row("lodges_at", "the attic of Brasswrights", valid_from_seq=9)
    old = _row(valid_from_seq=1)
    newer = _row(valid_from_seq=5)

    chosen = _select(_fact(), other, old, newer, cap=2)

    assert chosen == (newer, old)


def test_entity_objects_resolve_through_reused_temp_keys() -> None:
    place = uuid4()
    old = _row("located_in", None, object_entity_id=place)
    fact = _fact("located_in", None, object_ref="t1")

    assert _select(fact, old, refs={"t1": str(place)}) == ()
    assert _select(fact, old, refs={"t1": str(uuid4())}) == (old,)


def test_a_functional_predicate_retires_every_same_predicate_fact() -> None:
    first, second = _row(valid_from_seq=1), _row(valid_from_seq=2)

    claims, ambiguous = split_by_tier(
        [_pair(_fact(), first, second)], frozenset({"located_in"})
    )

    assert [claim.fact_id for claim in claims] == [
        str(first.fact_id),
        str(second.fact_id),
    ]
    assert {claim.reason for claim in claims} == {REASON_FUNCTIONAL}
    assert claims[0].evidence == ["S9.1"]
    assert ambiguous == []


def test_a_functional_predicate_never_retires_another_subjects_fact() -> None:
    elsewhere = _row()
    pair = FactCandidates(0, _fact(), uuid4(), (elsewhere,))

    claims, ambiguous = split_by_tier([pair], frozenset({"located_in"}))

    assert claims == []
    assert ambiguous[0].candidates == (elsewhere,)


def test_a_non_functional_predicate_goes_to_the_judge_untouched() -> None:
    old = _row("carries", "a lantern")

    claims, ambiguous = split_by_tier(
        [_pair(_fact("carries", "a map"), old)], frozenset({"located_in"})
    )

    assert claims == []
    assert [pair.candidates for pair in ambiguous] == [(old,)]


def test_other_predicate_candidates_of_a_functional_fact_stay_for_the_judge() -> None:
    same = _row("located_in", "the Wet Rope inn")
    related = _row("lodges_at", "the Wet Rope inn cellar")

    claims, ambiguous = split_by_tier(
        [_pair(_fact(), same, related)], frozenset({"located_in"})
    )

    assert [claim.fact_id for claim in claims] == [str(same.fact_id)]
    assert ambiguous[0].candidates == (related,)


def test_judge_output_is_limited_to_the_ids_offered_for_that_fact() -> None:
    offered = _row()
    pair = _pair(_fact(), offered)
    output = SupersessionJudgeOutput(
        judgements=[
            SupersessionJudgement(
                new_fact_index=0,
                superseded_fact_id=str(offered.fact_id),
                reason=" moved ",
            ),
            SupersessionJudgement(
                new_fact_index=0, superseded_fact_id=str(uuid4()), reason="invented"
            ),
            SupersessionJudgement(
                new_fact_index=7, superseded_fact_id=str(offered.fact_id), reason="x"
            ),
            SupersessionJudgement(
                new_fact_index=0, superseded_fact_id=None, reason="replaces nothing"
            ),
        ]
    )

    claims, drops = validate_judgements(output, [pair])

    assert [(claim.fact_id, claim.reason) for claim in claims] == [
        (str(offered.fact_id), "moved")
    ]
    assert drops == {DROP_JUDGE_UNOFFERED_ID: 1, DROP_JUDGE_BAD_INDEX: 1}


def test_merge_keeps_the_first_claim_per_fact_id() -> None:
    model = SupersessionClaim(fact_id="a", evidence=["S1.1"], reason="model")
    rule = SupersessionClaim(fact_id="a", evidence=["S2.1"], reason="rule")
    other = SupersessionClaim(fact_id="b", evidence=["S2.1"], reason="rule")

    assert merge_claims([model], [rule, other]) == [model, other]


def test_judge_input_lists_each_new_fact_with_its_ids_and_names() -> None:
    old = _row()
    names = {str(SUBJECT): "Pip"}

    text = render_judge_input(
        [_pair(_fact(), old, index=3)], {}, names, {3: "Pip moves to the attic."}
    )

    assert "[N3] Pip located in the Brasswrights attic" in text
    assert "evidence: Pip moves to the attic." in text
    assert f"[{old.fact_id}] Pip located in the Wet Rope inn" in text
