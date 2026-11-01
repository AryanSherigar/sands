"""RRF, the single-branch gate and the deterministic final order. Pure."""

from fractions import Fraction
from uuid import UUID

from app.services.fusion import (
    BRANCH_ORDER,
    Candidate,
    FusedCandidate,
    fuse,
    order_candidates,
)

RRF_K = 60
FLOOR = 20


def make_candidate(number: int, sequence: int = 1, kind: str = "fact") -> Candidate:
    return Candidate(kind, UUID(int=number), sequence)  # type: ignore[arg-type]


def run_fuse(rankings: dict) -> list[FusedCandidate]:
    return fuse(rankings, rrf_k=RRF_K, single_branch_rank_floor=FLOOR)


def by_number(fused: list[FusedCandidate]) -> dict[int, FusedCandidate]:
    return {item.candidate.item_id.int: item for item in fused}


def test_rrf_score_matches_a_hand_computed_example() -> None:
    a, b, d = make_candidate(1), make_candidate(2), make_candidate(4)
    rankings = {"exact": [a, b, d], "bm25": [b, a], "graph": [b]}

    fused = run_fuse(rankings)

    scores = {n: item.score for n, item in by_number(fused).items()}
    assert scores[1] == Fraction(1, 61) + Fraction(1, 62)
    assert scores[2] == Fraction(1, 62) + Fraction(1, 61) + Fraction(1, 61)
    assert scores[4] == Fraction(1, 63)
    assert [item.candidate.item_id.int for item in fused] == [2, 1, 4]
    assert float(scores[4]) == 1 / 63


def test_ranks_start_at_one_and_branches_follow_the_fixed_branch_order() -> None:
    a = make_candidate(1)
    rankings = {"graph": [a], "vector": [make_candidate(2), a], "exact": [a]}

    fused = by_number(run_fuse(rankings))[1]

    assert dict(fused.ranks) == {"exact": 1, "vector": 2, "graph": 1}
    assert fused.branches == ["exact", "vector", "graph"]
    assert BRANCH_ORDER == ("exact", "bm25", "vector", "graph")


def test_a_duplicate_inside_one_branch_keeps_its_best_rank_and_takes_no_rank() -> None:
    a, b = make_candidate(1), make_candidate(2)

    fused = by_number(run_fuse({"exact": [a, a, b]}))

    assert dict(fused[1].ranks) == {"exact": 1}
    assert dict(fused[2].ranks) == {"exact": 2}


def test_the_same_key_from_two_branches_is_one_candidate() -> None:
    a = make_candidate(1)

    fused = run_fuse({"exact": [a], "graph": [a]})

    assert len(fused) == 1


def test_the_same_id_with_a_different_kind_is_a_different_candidate() -> None:
    span = make_candidate(1, kind="span")
    fact = make_candidate(1, kind="fact")

    assert len(run_fuse({"exact": [span, fact]})) == 2


def branch_of_size(size: int) -> list[Candidate]:
    return [make_candidate(number) for number in range(1, size + 1)]


def test_gate_drops_a_bm25_only_candidate_at_rank_21_and_keeps_rank_20() -> None:
    fused = by_number(run_fuse({"bm25": branch_of_size(21)}))

    assert 20 in fused
    assert 21 not in fused
    assert len(fused) == FLOOR


def test_gate_applies_to_vector_only_candidates_too() -> None:
    fused = by_number(run_fuse({"vector": branch_of_size(22)}))

    assert set(fused) == set(range(1, FLOOR + 1))


def test_exact_only_and_graph_only_candidates_are_never_gated() -> None:
    fused = by_number(
        run_fuse(
            {
                "exact": branch_of_size(30),
                "graph": [make_candidate(100 + n) for n in range(30)],
            }
        )
    )

    assert len(fused) == 60


def test_a_candidate_in_two_branches_is_never_gated_even_at_a_deep_rank() -> None:
    target = make_candidate(500)
    deep = [*branch_of_size(30), target]
    rankings = {"bm25": deep, "vector": [*branch_of_size(35), target]}

    fused = by_number(run_fuse(rankings))

    assert 500 in fused
    assert set(fused[500].branches) == {"bm25", "vector"}


def test_a_deep_bm25_candidate_also_found_by_graph_survives() -> None:
    target = make_candidate(500)
    rankings = {"bm25": [*branch_of_size(30), target], "graph": [target]}

    assert 500 in by_number(run_fuse(rankings))


def test_a_bm25_and_exact_pair_is_not_gated() -> None:
    target = make_candidate(500)
    rankings = {"bm25": [*branch_of_size(30), target], "exact": [target]}

    assert 500 in by_number(run_fuse(rankings))


def test_equal_scores_break_by_sequence_descending_then_id_ascending() -> None:
    older = make_candidate(3, sequence=5)
    newer = make_candidate(9, sequence=8)
    same_low = make_candidate(1, sequence=8)
    rankings = {"exact": [older], "graph": [newer], "vector": [same_low]}

    fused = run_fuse(rankings)

    assert [item.candidate.item_id.int for item in fused] == [1, 9, 3]


def test_order_is_independent_of_input_order() -> None:
    items = run_fuse(
        {"exact": branch_of_size(6), "bm25": list(reversed(branch_of_size(6)))}
    )

    reordered = order_candidates(list(reversed(items)))

    assert reordered == items


def test_higher_score_beats_a_newer_sequence() -> None:
    both = make_candidate(1, sequence=1)
    newer = make_candidate(2, sequence=99)

    fused = run_fuse({"exact": [both, newer], "graph": [both]})

    assert fused[0].candidate == both


def test_mathematically_equal_scores_tie_and_fall_to_the_sequence_rule() -> None:
    a = make_candidate(1, sequence=1)
    b = make_candidate(2, sequence=2)
    c = make_candidate(3, sequence=3)
    rankings = {"exact": [a, c, b], "bm25": [b, a, c], "graph": [c, b, a]}

    fused = run_fuse(rankings)

    assert len({item.score for item in fused}) == 1
    assert [item.candidate.item_id.int for item in fused] == [3, 2, 1]


def test_empty_input_gives_no_candidates() -> None:
    assert run_fuse({}) == []
    assert run_fuse({"exact": [], "bm25": []}) == []
