from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import grant_ground
from app.engine.diplomacy.reputation import shift_standing
from app.models.world_diplomacy import (
    CommitmentState,
    CommitmentStatus,
    OathbreakerMark,
    TruceState,
)
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import (
    AllianceTerm,
    NonAggressionTerm,
    Term,
    VassalTerm,
)

PERCENT = 100
AGREEMENT_BREACHED = "agreement_breached"


def truce_between(
    world: WorldState, faction_a: FactionId, faction_b: FactionId
) -> TruceState | None:
    pair = {faction_a, faction_b}
    return next((t for t in world.truces if {t.faction_a, t.faction_b} == pair), None)


def expire_truces(world: WorldState) -> list[TruceState]:
    expired = [
        truce
        for truce in world.truces
        if truce.tier is not PeaceTier.PERPETUAL
        and truce.expires_turn < world.clock.turn
    ]
    world.truces = [truce for truce in world.truces if truce not in expired]
    return expired


def _term_pair(term: Term) -> set[FactionId]:
    if isinstance(term, VassalTerm):
        return {term.overlord_id, term.vassal_id}
    assert isinstance(term, NonAggressionTerm | AllianceTerm)
    return {term.faction_a, term.faction_b}


def _pacts_between(
    world: WorldState, first: FactionId, second: FactionId
) -> list[CommitmentState]:
    return [
        commitment
        for commitment in world.commitments
        if commitment.status == CommitmentStatus.ACTIVE
        and isinstance(commitment.term, NonAggressionTerm | AllianceTerm | VassalTerm)
        and _term_pair(commitment.term) == {first, second}
    ]


def _mark_oathbreaker(world: WorldState, breacher_id: FactionId) -> None:
    if all(mark.faction_id != breacher_id for mark in world.oathbreakers):
        world.oathbreakers.append(
            OathbreakerMark(faction_id=breacher_id, since_turn=world.clock.turn)
        )


def _grant_guarantor_grounds(
    world: WorldState,
    scenario: StrategyScenario,
    truces: list[TruceState],
    breacher_id: FactionId,
) -> None:
    guarantor_ids = sorted({g for truce in truces for g in truce.guarantor_ids})
    for guarantor_id in guarantor_ids:
        faction = world.factions[guarantor_id]
        if faction.is_destroyed or faction.leader_id is None:
            continue
        grant_ground(
            world,
            scenario,
            kind=GroundKind.BROKEN_PROMISE,
            holder_faction_id=guarantor_id,
            target_faction_id=breacher_id,
        )


def settle_hostages_on_breach(
    world: WorldState, truce_ids: set[str], breacher_id: FactionId
) -> None:
    for hostage in list(world.peace.hostages):
        if hostage.truce_id not in truce_ids:
            continue
        if breacher_id == hostage.giver_id:
            hostage.is_at_mercy = True
        else:
            world.peace.hostages.remove(hostage)


def breach_agreements(
    world: WorldState,
    scenario: StrategyScenario,
    breacher_id: FactionId,
    target_id: FactionId,
    cost_percent: int = PERCENT,
) -> list[EventLogEntry]:
    """Break every pact and truce between the pair, charging the breach cost once."""
    pair = {breacher_id, target_id}
    pacts = _pacts_between(world, breacher_id, target_id)
    truces = [t for t in world.truces if {t.faction_a, t.faction_b} == pair]
    if not pacts and not truces:
        return []
    for pact in pacts:
        pact.status = CommitmentStatus.BREACHED
    world.truces = [truce for truce in world.truces if truce not in truces]
    _mark_oathbreaker(world, breacher_id)
    tuning = scenario.tuning.diplomacy
    shift_standing(
        world.factions[breacher_id],
        -(tuning.breach_reputation_cost * cost_percent // PERCENT),
        -(tuning.breach_stability_cost * cost_percent // PERCENT),
    )
    settle_hostages_on_breach(world, {truce.id for truce in truces}, breacher_id)
    _grant_guarantor_grounds(world, scenario, truces, breacher_id)
    return [diplomacy_event(AGREEMENT_BREACHED, [breacher_id, target_id])]
