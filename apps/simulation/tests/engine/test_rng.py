import pytest
from app.engine.rng import DeterministicRng, derive_rng, derive_state

SEED_ZERO_VECTORS = [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]
SEQUENCE_LENGTH = 100
ROLL_SAMPLES = 1000
DIE_SIDES = 6


def test_seed_zero_matches_published_splitmix64_vectors() -> None:
    rng = DeterministicRng(0)
    assert [rng.next_u64() for _ in range(3)] == SEED_ZERO_VECTORS
    assert rng.draw_count == 3


def test_same_seed_gives_identical_sequences() -> None:
    first = DeterministicRng(123)
    second = DeterministicRng(123)
    assert [first.next_u64() for _ in range(SEQUENCE_LENGTH)] == [
        second.next_u64() for _ in range(SEQUENCE_LENGTH)
    ]


def test_resuming_from_saved_state_continues_the_sequence() -> None:
    original = DeterministicRng(7)
    for _ in range(5):
        original.next_u64()
    resumed = DeterministicRng(original.state, original.draw_count)
    assert resumed.next_u64() == original.next_u64()
    assert resumed.draw_count == original.draw_count


def test_roll_stays_in_range_and_hits_every_value() -> None:
    rng = DeterministicRng(99)
    values = {rng.roll(DIE_SIDES) for _ in range(ROLL_SAMPLES)}
    assert values == set(range(DIE_SIDES))


def test_roll_of_one_is_always_zero() -> None:
    rng = DeterministicRng(5)
    assert {rng.roll(1) for _ in range(20)} == {0}


@pytest.mark.parametrize("upper", [0, -1])
def test_non_positive_upper_is_rejected(upper: int) -> None:
    with pytest.raises(ValueError):
        DeterministicRng(1).roll(upper)


def test_derived_stream_is_stable_for_the_same_inputs() -> None:
    first = derive_rng(42, 3, "economy", "ashford")
    second = derive_rng(42, 3, "economy", "ashford")
    assert [first.next_u64() for _ in range(5)] == [second.next_u64() for _ in range(5)]


@pytest.mark.parametrize(
    "other",
    [
        (43, 3, "economy"),
        (42, 4, "economy"),
        (42, 3, "internal"),
        (42, 3, "economy", "x"),
    ],
)
def test_derived_streams_differ_when_any_input_differs(other: tuple) -> None:
    base = derive_rng(42, 3, "economy").next_u64()
    assert derive_rng(*other).next_u64() != base


def test_key_boundaries_cannot_collide() -> None:
    assert derive_state(1, "ab", "c") != derive_state(1, "a", "bc")


def test_fork_ignores_how_many_draws_the_parent_made() -> None:
    fresh = derive_rng(9, 1, "battles")
    used = derive_rng(9, 1, "battles")
    for _ in range(10):
        used.next_u64()
    assert fresh.fork("army_1").next_u64() == used.fork("army_1").next_u64()
    assert fresh.fork("army_1").next_u64() != fresh.fork("army_2").next_u64()


def test_roll_rejects_the_biased_tail() -> None:
    upper = (1 << 63) + 1
    rng = DeterministicRng(0)
    assert 0 <= rng.roll(upper) < upper


def test_roll_range_is_inclusive() -> None:
    rng = DeterministicRng(3)
    assert {rng.roll_range(-1, 1) for _ in range(ROLL_SAMPLES)} == {-1, 0, 1}


def test_shuffle_is_a_deterministic_permutation() -> None:
    items = list(range(20))
    first = DeterministicRng(11).shuffled(items)
    assert first == DeterministicRng(11).shuffled(items)
    assert sorted(first) == items
    assert first != items
    assert items == list(range(20))


def test_weighted_choice_skips_zero_weights_and_respects_totals() -> None:
    rng = DeterministicRng(2)
    picks = {
        rng.weighted_choice(["a", "b", "c"], [0, 5, 1]) for _ in range(ROLL_SAMPLES)
    }
    assert picks == {"b", "c"}


@pytest.mark.parametrize("weights", [[], [0, 0], [1, -1]])
def test_weighted_choice_rejects_unusable_weights(weights: list[int]) -> None:
    with pytest.raises(ValueError):
        DeterministicRng(2).weighted_choice(["a", "b"][: max(len(weights), 1)], weights)
