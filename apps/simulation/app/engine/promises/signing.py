from uuid import UUID

from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm

SWORN_PROMISE_MADE = "sworn_promise_made"


def _require_live_faction(world: WorldState, faction_id: str) -> None:
    faction = world.factions.get(faction_id)
    if faction is None or faction.is_destroyed:
        raise CampaignProgressError("invalid term", "invalid_term", 422)


def _require_known_region(world: WorldState, region_id: str | None) -> None:
    if region_id not in world.regions:
        raise CampaignProgressError("invalid term", "invalid_term", 422)


def _require_valid_parties(world: WorldState, term: SwornPromiseTerm) -> None:
    _require_live_faction(world, term.promisor_id)
    _require_live_faction(world, term.beneficiary_id)
    if term.promise is PromiseKind.NEVER_ALLY_WITH:
        assert term.subject_id is not None
        _require_live_faction(world, term.subject_id)
    if term.promise is PromiseKind.NEVER_OCCUPY_REGION:
        _require_known_region(world, term.subject_id)


def _is_same_promise(first: SwornPromiseTerm, second: SwornPromiseTerm) -> bool:
    return (
        first.promisor_id,
        first.beneficiary_id,
        first.promise,
        first.subject_id,
    ) == (second.promisor_id, second.beneficiary_id, second.promise, second.subject_id)


def _has_active_equal(world: WorldState, term: SwornPromiseTerm) -> bool:
    return any(
        commitment.status is CommitmentStatus.ACTIVE
        and isinstance(commitment.term, SwornPromiseTerm)
        and _is_same_promise(commitment.term, term)
        for commitment in world.commitments
    )


def is_promise_in_force(world: WorldState, term: SwornPromiseTerm) -> bool:
    return _has_active_equal(world, term)


def sign_sworn_promise(
    world: WorldState, term: SwornPromiseTerm, origin_scene_id: UUID | None
) -> list[EventLogEntry]:
    _require_valid_parties(world, term)
    if _has_active_equal(world, term):
        return []
    number = next_counter(world, CounterKind.COMMITMENT)
    world.commitments.append(
        CommitmentState(
            id=f"commitment_{number}",
            term=term,
            start_turn=world.clock.turn,
            end_turn=world.clock.turn + term.duration_turns,
            origin_scene_id=origin_scene_id,
        )
    )
    return [
        diplomacy_event(
            SWORN_PROMISE_MADE,
            [term.promisor_id, term.beneficiary_id],
            {"duration_turns": term.duration_turns},
            is_major=True,
        )
    ]
