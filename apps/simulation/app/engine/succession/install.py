from dataclasses import dataclass

from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import inherit_grounds
from app.engine.peace.succession import leader_died
from app.engine.pressure.shocks import record_shock
from app.engine.pressure.wars import wars_of
from app.engine.succession.crisis import (
    crisis_of,
    drop_crisis,
    open_minor_heir_regency,
    open_regency_crisis,
)
from app.engine.succession.heirs import (
    find_heir_by_id,
    find_heir_setup,
    leader_from_heir,
    regent_leader,
)
from app.engine.succession.opinions import carry_opinions
from app.engine.succession.roll import mortal_ruler
from app.models.world_character import LeaderState
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState
from app.models.world_succession import CrisisState
from strategy_contracts.ids import FactionId
from strategy_contracts.pressure import ShockKind
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HeirSetup

CAUSE_EVENT = "event"
EVENT_RULER_DIED = "ruler_died"
EVENT_RULER_SUCCEEDED = "ruler_succeeded"


@dataclass(frozen=True)
class SuccessionPlan:
    leader: LeaderState
    crisis: CrisisState | None


def _heir_for(
    world: WorldState, scenario: StrategyScenario, dead: LeaderState
) -> HeirSetup | None:
    crisis = crisis_of(world, dead.faction_id)
    if crisis is not None and crisis.heir_id is not None:
        return find_heir_by_id(scenario, crisis.heir_id)
    return find_heir_setup(scenario, dead.id)


def _regency_plan(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    heir: HeirSetup | None,
) -> SuccessionPlan:
    regent = regent_leader(faction_id, scenario)
    if heir is None:
        return SuccessionPlan(
            regent, open_regency_crisis(world, scenario, faction_id, regent.id)
        )
    crisis = open_minor_heir_regency(world, scenario, faction_id, regent.id, heir)
    return SuccessionPlan(regent, crisis)


def _plan_succession(
    world: WorldState, scenario: StrategyScenario, dead: LeaderState
) -> SuccessionPlan:
    heir = _heir_for(world, scenario, dead)
    if heir is None or heir.id in world.leaders:
        return _regency_plan(world, scenario, dead.faction_id, None)
    if heir.age >= scenario.tuning.succession.coming_of_age:
        leader = leader_from_heir(heir, dead.faction_id)
        return SuccessionPlan(leader, None)
    return _regency_plan(world, scenario, dead.faction_id, heir)


def _seat(world: WorldState, scenario: StrategyScenario, plan: SuccessionPlan) -> None:
    faction = world.factions[plan.leader.faction_id]
    world.leaders[plan.leader.id] = plan.leader
    if faction.leader_id is not None:
        carry_opinions(world, scenario, faction.leader_id, plan.leader.id)
    faction.leader_id = plan.leader.id
    drop_crisis(world, faction.id)
    if plan.crisis is not None:
        world.succession.crises.append(plan.crisis)
    inherit_grounds(world, scenario, faction.id, plan.leader.id)


def _record_shocks(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> None:
    for war in wars_of(world, faction_id):
        record_shock(world, scenario, ShockKind.RULER_DIED, faction_id, war.id)


def _succession_events(
    dead: LeaderState, plan: SuccessionPlan, cause: str, phase: PhaseName
) -> list[EventLogEntry]:
    faction_id = dead.faction_id
    return [
        diplomacy_event(
            EVENT_RULER_DIED, [dead.id, faction_id, cause], phase=phase, is_major=True
        ),
        diplomacy_event(
            EVENT_RULER_SUCCEEDED,
            [dead.id, plan.leader.id, faction_id],
            phase=phase,
            is_major=True,
        ),
    ]


def kill_ruler(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    cause: str,
    phase: PhaseName = PhaseName.TIME,
) -> list[EventLogEntry]:
    dead = mortal_ruler(world, faction_id)
    if dead is None or not world.succession_ruleset:
        return []
    dead.is_alive = False
    plan = _plan_succession(world, scenario, dead)
    _seat(world, scenario, plan)
    _record_shocks(world, scenario, faction_id)
    lapses = [
        event.model_copy(update={"phase": phase})
        for event in leader_died(world, scenario, dead.id)
    ]
    return _succession_events(dead, plan, cause, phase) + lapses
