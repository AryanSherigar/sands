from app.engine.diplomacy.events import diplomacy_event
from app.engine.succession.heirs import find_heir_by_id, leader_from_heir
from app.engine.succession.opinions import carry_opinions
from app.models.world_clock import TURNS_PER_YEAR
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from app.models.world_succession import CrisisState
from strategy_contracts.ids import FactionId, LeaderId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HeirSetup


def crisis_of(world: WorldState, faction_id: FactionId) -> CrisisState | None:
    return next(
        (item for item in world.succession.crises if item.faction_id == faction_id),
        None,
    )


def drop_crisis(world: WorldState, faction_id: FactionId) -> None:
    world.succession.crises = [
        item for item in world.succession.crises if item.faction_id != faction_id
    ]


def open_regency_crisis(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    regent_id: LeaderId,
) -> CrisisState:
    return CrisisState(
        faction_id=faction_id,
        ends_turn=world.clock.turn + scenario.tuning.succession.crisis_turns,
        regent_id=regent_id,
        is_penalty_active=True,
    )


def open_minor_heir_regency(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    regent_id: LeaderId,
    heir: HeirSetup,
) -> CrisisState:
    years_left = scenario.tuning.succession.coming_of_age - heir.age
    return CrisisState(
        faction_id=faction_id,
        ends_turn=0,
        regent_id=regent_id,
        heir_id=heir.id,
        heir_comes_of_age_turn=world.clock.turn + years_left * TURNS_PER_YEAR,
        is_penalty_active=False,
    )


def _hand_grounds_to(
    world: WorldState, crisis: CrisisState, leader_id: LeaderId
) -> None:
    for ground in world.grounds:
        if ground.holder_leader_id == crisis.regent_id:
            ground.inherited_from_leader_id = crisis.regent_id
            ground.holder_leader_id = leader_id


def _hand_over_to_heir(
    world: WorldState, scenario: StrategyScenario, crisis: CrisisState
) -> list[EventLogEntry]:
    heir = find_heir_by_id(scenario, crisis.heir_id or "")
    faction = world.factions[crisis.faction_id]
    drop_crisis(world, crisis.faction_id)
    if heir is None:
        return []
    leader = leader_from_heir(heir, faction.id)
    leader.age = max(leader.age, scenario.tuning.succession.coming_of_age)
    regent = world.leaders.get(crisis.regent_id)
    if regent is not None:
        regent.is_alive = False
    _hand_grounds_to(world, crisis, leader.id)
    world.leaders[leader.id] = leader
    carry_opinions(world, scenario, crisis.regent_id, leader.id)
    faction.leader_id = leader.id
    return [_crisis_event("heir_came_of_age", [leader.id, faction.id])]


def _crisis_event(kind: str, subject_ids: list[str]) -> EventLogEntry:
    return diplomacy_event(kind, subject_ids, phase=PhaseName.TIME, is_major=True)


def _advance(
    world: WorldState, scenario: StrategyScenario, crisis: CrisisState
) -> list[EventLogEntry]:
    turn = world.clock.turn
    if world.factions[crisis.faction_id].is_destroyed:
        drop_crisis(world, crisis.faction_id)
        return []
    if crisis.heir_id is not None:
        is_of_age = turn >= (crisis.heir_comes_of_age_turn or 0)
        return _hand_over_to_heir(world, scenario, crisis) if is_of_age else []
    if turn < crisis.ends_turn:
        return []
    drop_crisis(world, crisis.faction_id)
    return [_crisis_event("crisis_ended", [crisis.regent_id, crisis.faction_id])]


def tick_crises(world: WorldState, scenario: StrategyScenario) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for crisis in sorted(world.succession.crises, key=lambda item: item.faction_id):
        events += _advance(world, scenario, crisis)
    return events
