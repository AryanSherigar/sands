from app.engine.alliances.calls import is_callable, is_hostile_pair
from app.engine.alliances.joining import join_war
from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.pressure.wars import side_of
from app.engine.vassals.registry import vassal_term, vassals_of
from app.models.world_alliance import CallKind, CallToArmsState
from app.models.world_diplomacy import CommitmentState, WarState
from app.models.world_events import EventLogEntry
from app.models.world_region import RegionState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario

LEVY_RAISED = "levy_raised"


def _levy_call(
    world: WorldState, war: WarState, commitment: CommitmentState
) -> CallToArmsState:
    term = vassal_term(commitment)
    side = side_of(war, term.overlord_id)
    assert side is not None
    return CallToArmsState(
        id=f"call_{next_counter(world, CounterKind.CALL)}",
        alliance_id=commitment.id,
        war_id=war.id,
        caller_id=term.overlord_id,
        ally_id=term.vassal_id,
        side=side,
        issued_turn=world.clock.turn,
        deadline_turn=world.clock.turn,
        is_defensive=False,
        kind=CallKind.LEVY,
    )


def _is_levyable(world: WorldState, war: WarState, commitment: CommitmentState) -> bool:
    term = vassal_term(commitment)
    if term.levy_share_percent == 0:
        return False
    if not is_callable(world, war, term.overlord_id, term.vassal_id):
        return False
    return not is_hostile_pair(world, term.overlord_id, term.vassal_id)


def issue_levy_calls(world: WorldState, war: WarState) -> list[CallToArmsState]:
    calls: list[CallToArmsState] = []
    for principal_id in (war.attacker_id, war.defender_id):
        for commitment in vassals_of(world, principal_id):
            if _is_levyable(world, war, commitment):
                calls.append(_levy_call(world, war, commitment))
    return calls


def _owned_by(world: WorldState, faction_id: FactionId) -> list[RegionState]:
    return [
        region
        for _, region in sorted(world.regions.items())
        if region.owner_id == faction_id
    ]


def _capital_of(world: WorldState, faction_id: FactionId) -> RegionState | None:
    capital_id = world.factions[faction_id].capital_region_id
    if capital_id in world.regions and world.regions[capital_id].owner_id == faction_id:
        return world.regions[capital_id]
    owned = _owned_by(world, faction_id)
    return owned[0] if owned else None


def move_levied_manpower(
    world: WorldState, overlord_id: FactionId, vassal_id: FactionId, share_percent: int
) -> int:
    capital = _capital_of(world, overlord_id)
    if capital is None:
        return 0
    moved = 0
    for region in _owned_by(world, vassal_id):
        taken = region.manpower * share_percent // FULL_SHARE_PERCENT
        region.manpower -= taken
        moved += taken
    capital.manpower += moved
    return moved


def apply_levy(
    world: WorldState, scenario: StrategyScenario, call: CallToArmsState
) -> list[EventLogEntry]:
    commitment = next(item for item in world.commitments if item.id == call.alliance_id)
    share = vassal_term(commitment).levy_share_percent
    events = join_war(world, scenario, call)
    moved = move_levied_manpower(world, call.caller_id, call.ally_id, share)
    events.append(
        diplomacy_event(
            LEVY_RAISED,
            [call.war_id, call.ally_id, call.caller_id],
            {"manpower": moved},
        )
    )
    return events


def raise_levies(
    world: WorldState, scenario: StrategyScenario, war: WarState
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for call in issue_levy_calls(world, war):
        events += apply_levy(world, scenario, call)
    return events
