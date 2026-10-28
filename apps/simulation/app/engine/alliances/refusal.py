from app.engine.alliances.registry import (
    alliance_term,
    restore_peace_after_alliance,
)
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import grant_ground
from app.engine.opinion import shift_opinion
from app.engine.peace.truces import breach_agreements
from app.engine.vassals.protection import refuse_protection
from app.models.world_alliance import AllianceStanding, CallKind, CallToArmsState
from app.models.world_diplomacy import CommitmentState, CommitmentStatus
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.alliance import AllianceType
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.ids import FactionId
from strategy_contracts.pressure import ShockKind
from strategy_contracts.scenario import StrategyScenario

CALL_REFUSED = "call_refused"
ALLIANCE_BROKEN = "alliance_broken"
REFUSED_CALL_CAUSE = "refused_call"


def _standing_for(world: WorldState, alliance_id: str) -> AllianceStanding:
    standing = next(
        (item for item in world.alliance.standing if item.alliance_id == alliance_id),
        None,
    )
    if standing is None:
        standing = AllianceStanding(alliance_id=alliance_id)
        world.alliance.standing.append(standing)
    return standing


def _is_facing_destruction(world: WorldState, faction_id: FactionId) -> bool:
    return any(
        shock.faction_id == faction_id and shock.kind == ShockKind.CAPITAL_FALLS
        for shock in world.pressure.shocks
    )


def _partner(commitment: CommitmentState, faction_id: FactionId) -> FactionId:
    term = alliance_term(commitment)
    return term.faction_b if term.faction_a == faction_id else term.faction_a


def break_alliance(
    world: WorldState,
    scenario: StrategyScenario,
    breacher_id: FactionId,
    alliance: CommitmentState,
) -> list[EventLogEntry]:
    if alliance.status is not CommitmentStatus.ACTIVE:
        return []
    injured_id = _partner(alliance, breacher_id)
    events = breach_agreements(world, scenario, breacher_id, injured_id)
    restore_peace_after_alliance(world, breacher_id, injured_id)
    is_defensive = alliance_term(alliance).alliance_type is AllianceType.DEFENSIVE
    if is_defensive and world.factions[injured_id].leader_id is not None:
        grant_ground(
            world,
            scenario,
            kind=GroundKind.BROKEN_PROMISE,
            holder_faction_id=injured_id,
            target_faction_id=breacher_id,
        )
    world.alliance.calls = [
        item for item in world.alliance.calls if item.alliance_id != alliance.id
    ]
    events.append(diplomacy_event(ALLIANCE_BROKEN, [breacher_id, injured_id]))
    return events


def _should_break(
    world: WorldState,
    scenario: StrategyScenario,
    call: CallToArmsState,
    refusals: int,
) -> bool:
    tuning = scenario.tuning.alliance
    if refusals >= tuning.refusal_breaks_alliance_after:
        return True
    return tuning.is_destruction_refusal_breaking and _is_facing_destruction(
        world, call.caller_id
    )


def refuse_call(
    world: WorldState, scenario: StrategyScenario, call: CallToArmsState
) -> list[EventLogEntry]:
    if call.kind is CallKind.PROTECTION:
        return refuse_protection(world, scenario, call)
    tuning = scenario.tuning.alliance
    cost = (
        tuning.refusal_opinion_cost_defensive
        if call.is_defensive
        else tuning.refusal_opinion_cost_offensive
    )
    shift_opinion(
        world,
        call.caller_id,
        call.ally_id,
        REFUSED_CALL_CAUSE,
        -cost,
        tuning.opinion_fade_per_turn,
    )
    events = [
        diplomacy_event(CALL_REFUSED, [call.war_id, call.ally_id, call.caller_id])
    ]
    standing = _standing_for(world, call.alliance_id)
    refusals = standing.refusals_by_faction.get(call.ally_id, 0) + 1
    standing.refusals_by_faction[call.ally_id] = refusals
    alliance = next((c for c in world.commitments if c.id == call.alliance_id), None)
    if alliance is not None and _should_break(world, scenario, call, refusals):
        events += break_alliance(world, scenario, call.ally_id, alliance)
    return events
