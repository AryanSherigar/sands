from app.engine.alliances.calls import is_callable, is_hostile_pair
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.opinion import shift_opinion
from app.engine.peace.truces import breach_agreements
from app.engine.pressure.wars import side_of
from app.engine.vassals.registry import vassal_term, vassalage_of
from app.models.world_alliance import CallKind, CallToArmsState
from app.models.world_diplomacy import CommitmentState, CommitmentStatus, WarState
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

VASSAL_FREED = "vassal_freed"
REFUSED_PROTECTION_CAUSE = "refused_protection"


def issue_protection_calls(
    world: WorldState, scenario: StrategyScenario, war: WarState
) -> list[CallToArmsState]:
    commitment = vassalage_of(world, war.defender_id)
    if commitment is None:
        return []
    term = vassal_term(commitment)
    if not is_callable(world, war, term.vassal_id, term.overlord_id):
        return []
    if is_hostile_pair(world, term.vassal_id, term.overlord_id):
        return []
    side = side_of(war, term.vassal_id)
    assert side is not None
    call = CallToArmsState(
        id=f"call_{next_counter(world, CounterKind.CALL)}",
        alliance_id=commitment.id,
        war_id=war.id,
        caller_id=term.vassal_id,
        ally_id=term.overlord_id,
        side=side,
        issued_turn=world.clock.turn,
        deadline_turn=world.clock.turn + scenario.tuning.alliance.call_answer_turns,
        is_defensive=True,
        kind=CallKind.PROTECTION,
    )
    world.alliance.calls.append(call)
    return [call]


def free_vassal(
    world: WorldState,
    scenario: StrategyScenario,
    overlord_id: FactionId,
    commitment: CommitmentState,
) -> list[EventLogEntry]:
    if commitment.status is not CommitmentStatus.ACTIVE:
        return []
    vassal_id = vassal_term(commitment).vassal_id
    events = breach_agreements(world, scenario, overlord_id, vassal_id)
    commitment.status = CommitmentStatus.BREACHED
    events.append(diplomacy_event(VASSAL_FREED, [overlord_id, vassal_id]))
    return events


def refuse_protection(
    world: WorldState, scenario: StrategyScenario, call: CallToArmsState
) -> list[EventLogEntry]:
    tuning = scenario.tuning.alliance
    shift_opinion(
        world,
        call.caller_id,
        call.ally_id,
        REFUSED_PROTECTION_CAUSE,
        -tuning.refusal_opinion_cost_defensive,
        tuning.opinion_fade_per_turn,
    )
    commitment = next(
        (item for item in world.commitments if item.id == call.alliance_id), None
    )
    if commitment is None:
        return []
    return free_vassal(world, scenario, call.ally_id, commitment)
