from app.models.world_character import LeaderState, MemoryState
from strategy_contracts.scene import TermsResult

PACT_SIGNED = "pact_signed"
TALKS_REFUSED = "talks_refused"
TALKS_BROKEN_OFF = "talks_broken_off"
MEMORY_WEIGHTS = {
    TermsResult.AGREED: (PACT_SIGNED, 12),
    TermsResult.REFUSED: (TALKS_REFUSED, -6),
    TermsResult.WALKED_OUT: (TALKS_BROKEN_OFF, -12),
}
TALKS_HELD = "talks_held"
TALKS_HELD_WEIGHT = 3
MEMORY_DECAY_PER_TURN = 1
MAX_MEMORIES = 8


def _remaining_weight(memory: MemoryState, turn: int) -> int:
    """Weight shrinks toward zero by a fixed amount per turn and never changes sign."""
    magnitude = max(
        0, abs(memory.weight) - MEMORY_DECAY_PER_TURN * (turn - memory.turn)
    )
    return magnitude if memory.weight > 0 else -magnitude


def memory_warmth(leader: LeaderState, subject_id: str | None, turn: int) -> int:
    return sum(
        _remaining_weight(memory, turn)
        for memory in leader.memories
        if memory.subject_id == subject_id
    )


def _memory_rank(memory: MemoryState, turn: int) -> tuple[int, int, str]:
    return abs(_remaining_weight(memory, turn)), memory.turn, memory.kind


def _remember(
    leader: LeaderState, kind: str, weight: int, subject_id: str | None, turn: int
) -> None:
    leader.memories.append(
        MemoryState(kind=kind, turn=turn, subject_id=subject_id, weight=weight)
    )
    leader.memories.sort(key=lambda memory: _memory_rank(memory, turn), reverse=True)
    del leader.memories[MAX_MEMORIES:]


def record_negotiation_memory(
    leader: LeaderState, subject_id: str | None, turn: int, result: TermsResult
) -> None:
    kind, weight = MEMORY_WEIGHTS[result]
    _remember(leader, kind, weight, subject_id, turn)


def record_talks_memory(
    leader: LeaderState, subject_id: str | None, turn: int, is_accepted: bool
) -> None:
    if is_accepted:
        _remember(leader, TALKS_HELD, TALKS_HELD_WEIGHT, subject_id, turn)
        return
    record_negotiation_memory(leader, subject_id, turn, TermsResult.REFUSED)
