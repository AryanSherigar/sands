from app.engine.diplomacy.events import diplomacy_event
from app.engine.economy.income import faction_income
from app.engine.economy.ledger import available_cash, change_treasury
from app.engine.opinion import shift_opinion
from app.engine.vassals.independence import start_independence_war
from app.engine.vassals.levy import move_levied_manpower
from app.engine.vassals.overreach import HALF_DIVISOR, raise_unrest
from app.engine.vassals.registry import vassalage_by_id
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from app.models.world_vassal import DemandState, VassalStanding
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.vassal import DemandKind, DemandReply

DEMAND_PAID = "demand_paid"
DEMAND_REFUSED = "demand_refused"
REFUSED_DEMAND_CAUSE = "refused_demand"


def _standing_for(world: WorldState, vassalage_id: str) -> VassalStanding:
    standing = next(
        (item for item in world.vassal.standing if item.vassalage_id == vassalage_id),
        None,
    )
    if standing is None:
        standing = VassalStanding(vassalage_id=vassalage_id)
        world.vassal.standing.append(standing)
    return standing


def _pay_tribute(
    world: WorldState, scenario: StrategyScenario, demand: DemandState, percent: int
) -> int:
    income = faction_income(world, scenario.tuning.economy, demand.vassal_id).total
    vassal = world.factions[demand.vassal_id]
    amount = min(income * percent // FULL_SHARE_PERCENT, available_cash(vassal))
    change_treasury(vassal, -amount)
    change_treasury(world.factions[demand.overlord_id], amount)
    return amount


def _grant_access(
    world: WorldState, scenario: StrategyScenario, demand: DemandState, turns: int
) -> int:
    world.vassal.garrison_until[demand.vassalage_id] = world.clock.turn + turns
    return turns


def _pay(
    world: WorldState,
    scenario: StrategyScenario,
    demand: DemandState,
    reply: DemandReply,
) -> list[EventLogEntry]:
    tuning = scenario.tuning.vassal
    is_counter = reply is DemandReply.COUNTER
    asked = demand.amount
    if is_counter:
        asked = demand.granted + (demand.amount - demand.granted) // HALF_DIVISOR
    if demand.kind is DemandKind.TRIBUTE:
        paid = _pay_tribute(world, scenario, demand, asked)
    elif demand.kind is DemandKind.LEVY:
        paid = move_levied_manpower(world, demand.overlord_id, demand.vassal_id, asked)
    else:
        turns = tuning.garrison_demand_turns // (HALF_DIVISOR if is_counter else 1)
        paid = _grant_access(world, scenario, demand, max(1, turns))
    return [
        diplomacy_event(
            DEMAND_PAID, [demand.overlord_id, demand.vassal_id], {"paid": paid}
        )
    ]


def _refuse(
    world: WorldState,
    scenario: StrategyScenario,
    demand: DemandState,
    reply: DemandReply,
) -> list[EventLogEntry]:
    tuning = scenario.tuning.vassal
    is_strong = reply is DemandReply.REFUSE_STRONGLY
    cost = tuning.strong_opinion_cost if is_strong else tuning.refuse_opinion_cost
    grievance = tuning.strong_grievance if is_strong else tuning.refuse_grievance
    shift_opinion(
        world,
        demand.vassal_id,
        demand.overlord_id,
        REFUSED_DEMAND_CAUSE,
        -cost,
        tuning.opinion_fade_per_turn,
    )
    _standing_for(world, demand.vassalage_id).grievance += grievance
    if is_strong:
        raise_unrest(world, scenario, demand)
    return [diplomacy_event(DEMAND_REFUSED, [demand.vassal_id, demand.overlord_id])]


def apply_reply(
    world: WorldState,
    scenario: StrategyScenario,
    demand: DemandState,
    reply: DemandReply,
) -> list[EventLogEntry]:
    if reply in (DemandReply.ACCEPT, DemandReply.COUNTER):
        return _pay(world, scenario, demand, reply)
    if reply is DemandReply.REBEL:
        commitment = vassalage_by_id(world, demand.vassalage_id)
        assert commitment is not None
        return start_independence_war(world, scenario, commitment)
    return _refuse(world, scenario, demand, reply)
