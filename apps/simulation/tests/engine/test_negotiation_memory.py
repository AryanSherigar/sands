from app.engine import negotiation
from app.engine.negotiation_memory import (
    MAX_MEMORIES,
    MEMORY_DECAY_PER_TURN,
    PACT_SIGNED,
    TALKS_BROKEN_OFF,
    TALKS_REFUSED,
    memory_warmth,
    record_negotiation_memory,
)
from app.models.world_character import LeaderState, MemoryState
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scene import TermsResult

from tests.engine.test_negotiation import PLAYER, RIVAL, TURN, _world

SUBJECT = "valdren"


def _closed(result: TermsResult | None, card=None):
    world = negotiation.open_negotiation(_world(["pragmatic"]), RIVAL, "talk")
    return negotiation.close_negotiation(
        world, load_three_crowns(), world.progress.pending_scene_id, card, result
    )[0]


def _accept_at(world) -> int:
    return negotiation.acceptance_range(
        world, load_three_crowns(), PLAYER, RIVAL
    ).accept_at


def _leader() -> LeaderState:
    return LeaderState(id="mira", name="Mira", faction_id=RIVAL, age=40)


def test_each_outcome_leaves_a_distinct_memory_on_the_counterpart() -> None:
    kinds = {
        result: _closed(result).leaders["mira"].memories[0].kind
        for result in TermsResult
    }
    assert kinds == {
        TermsResult.AGREED: PACT_SIGNED,
        TermsResult.REFUSED: TALKS_REFUSED,
        TermsResult.WALKED_OUT: TALKS_BROKEN_OFF,
    }
    memory = _closed(TermsResult.REFUSED).leaders["mira"].memories[0]
    assert (memory.subject_id, memory.turn) == (SUBJECT, TURN)


def test_a_missing_result_is_inferred_from_the_card() -> None:
    assert _closed(None).leaders["mira"].memories[0].kind == TALKS_REFUSED


def test_closing_clears_the_counterpart_marker() -> None:
    assert _closed(TermsResult.REFUSED).progress.negotiation_counterpart_id is None


def test_a_scene_opened_before_memory_existed_records_nothing() -> None:
    world = _world(["pragmatic"])
    world.progress.pending_scene_id = negotiation.negotiation_scene_id(world, "old")
    closed, _ = negotiation.close_negotiation(
        world,
        load_three_crowns(),
        world.progress.pending_scene_id,
        None,
        TermsResult.REFUSED,
    )
    assert closed.leaders["mira"].memories == []


def test_warmth_fades_each_turn_and_never_flips_sign() -> None:
    leader = _leader()
    leader.memories = [
        MemoryState(kind=PACT_SIGNED, turn=2, subject_id=SUBJECT, weight=12),
        MemoryState(kind=TALKS_REFUSED, turn=2, subject_id=SUBJECT, weight=-6),
    ]
    fresh = memory_warmth(leader, SUBJECT, 2)
    later = memory_warmth(leader, SUBJECT, 2 + 8 * MEMORY_DECAY_PER_TURN)
    assert fresh == 6
    assert later == 4
    assert memory_warmth(leader, SUBJECT, 200) == 0
    assert memory_warmth(leader, "someone_else", 2) == 0


def test_memories_are_capped_and_the_strongest_survive() -> None:
    leader = _leader()
    for turn in range(MAX_MEMORIES + 3):
        record_negotiation_memory(leader, SUBJECT, turn, TermsResult.REFUSED)
    record_negotiation_memory(leader, SUBJECT, MAX_MEMORIES + 3, TermsResult.AGREED)
    assert len(leader.memories) == MAX_MEMORIES
    assert leader.memories[0].kind == PACT_SIGNED


def test_a_past_pact_lowers_the_bar_and_a_broken_off_talk_raises_it() -> None:
    baseline = _accept_at(_world(["pragmatic"]))
    warm = _closed(TermsResult.AGREED, card=None)
    cold = _closed(TermsResult.WALKED_OUT)
    assert _accept_at(warm) < baseline < _accept_at(cold)


def test_no_memory_leaves_the_range_unchanged() -> None:
    world = _world(["pragmatic"])
    assert memory_warmth(world.leaders["mira"], SUBJECT, TURN) == 0
