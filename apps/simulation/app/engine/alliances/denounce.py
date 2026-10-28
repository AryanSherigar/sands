from app.engine.alliances.registry import (
    alliance_term,
    restore_peace_after_alliance,
)
from app.engine.diplomacy.events import diplomacy_event
from app.engine.opinion import shift_opinion
from app.exceptions.command_exceptions import CommandError
from app.models.orders import DenounceAllianceOrder
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import AllianceTerm

ALLIANCE_DENOUNCED = "alliance_denounced"
ALLIANCE_EXPIRED = "alliance_expired"
DENOUNCED_CAUSE = "denounced_alliance"
HTTP_UNPROCESSABLE = 422


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def _active_alliance(world: WorldState, alliance_id: str) -> CommitmentState | None:
    return next(
        (
            item
            for item in world.commitments
            if item.id == alliance_id
            and isinstance(item.term, AllianceTerm)
            and item.status is CommitmentStatus.ACTIVE
        ),
        None,
    )


def validate_denounce(world: WorldState, order: DenounceAllianceOrder) -> None:
    alliance = _active_alliance(world, order.alliance_id)
    if alliance is None:
        raise _reject("unknown_alliance")
    term = alliance_term(alliance)
    if order.faction_id not in {term.faction_a, term.faction_b}:
        raise _reject("not_member")


def denounce_alliance(
    world: WorldState, scenario: StrategyScenario, order: DenounceAllianceOrder
) -> list[EventLogEntry]:
    validate_denounce(world, order)
    alliance = _active_alliance(world, order.alliance_id)
    assert alliance is not None
    term = alliance_term(alliance)
    partner_id = (
        term.faction_b if term.faction_a == order.faction_id else term.faction_a
    )
    alliance.status = CommitmentStatus.EXPIRED
    restore_peace_after_alliance(world, order.faction_id, partner_id)
    tuning = scenario.tuning.alliance
    shift_opinion(
        world,
        partner_id,
        order.faction_id,
        DENOUNCED_CAUSE,
        -tuning.denounce_opinion_cost,
        tuning.opinion_fade_per_turn,
    )
    return [diplomacy_event(ALLIANCE_DENOUNCED, [order.faction_id, partner_id])]


def expire_alliances(world: WorldState) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for item in sorted(world.commitments, key=lambda commitment: commitment.id):
        is_alliance = isinstance(item.term, AllianceTerm)
        is_due = item.end_turn is not None and item.end_turn <= world.clock.turn
        if not (is_alliance and is_due and item.status is CommitmentStatus.ACTIVE):
            continue
        item.status = CommitmentStatus.EXPIRED
        term = alliance_term(item)
        restore_peace_after_alliance(world, term.faction_a, term.faction_b)
        events.append(
            diplomacy_event(
                ALLIANCE_EXPIRED,
                [term.faction_a, term.faction_b],
                phase=PhaseName.TIME,
            )
        )
    return events
