from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.vassals.consequences import apply_reply
from app.engine.vassals.overreach import demand_figures, raise_unrest
from app.engine.vassals.registry import vassal_term, vassalage_by_id
from app.engine.vassals.reply import choose_reply
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AnswerDemandOrder, DemandFromVassalOrder
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from app.models.world_vassal import DemandState
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.vassal import DemandKind, DemandReply

DEMAND_ISSUED = "demand_issued"
DEMAND_ANSWERED = "demand_answered"
HTTP_UNPROCESSABLE = 422


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def _is_on_cooldown(
    world: WorldState, scenario: StrategyScenario, vassalage_id: str
) -> bool:
    last = world.vassal.last_demand_turn.get(vassalage_id)
    cooldown = scenario.tuning.vassal.demand_cooldown_turns
    return last is not None and world.clock.turn - last < cooldown


def validate_demand_from_vassal(
    world: WorldState, scenario: StrategyScenario, order: DemandFromVassalOrder
) -> None:
    commitment = vassalage_by_id(world, order.vassalage_id)
    if commitment is None:
        raise _reject("unknown_vassalage")
    if vassal_term(commitment).overlord_id != order.faction_id:
        raise _reject("not_overlord")
    if (
        order.demand_kind is not DemandKind.GARRISON
        and order.amount > FULL_SHARE_PERCENT
    ):
        raise _reject("bad_amount")
    if any(item.vassalage_id == commitment.id for item in world.vassal.demands):
        raise _reject("demand_pending")
    if _is_on_cooldown(world, scenario, commitment.id):
        raise _reject("demand_cooldown")
    figures = demand_figures(
        commitment, order.demand_kind, order.amount, scenario.tuning.vassal
    )
    if figures.excess <= 0:
        raise _reject("no_excess")


def issue_demand(
    world: WorldState, scenario: StrategyScenario, order: DemandFromVassalOrder
) -> list[EventLogEntry]:
    commitment = vassalage_by_id(world, order.vassalage_id)
    assert commitment is not None
    term = vassal_term(commitment)
    figures = demand_figures(
        commitment, order.demand_kind, order.amount, scenario.tuning.vassal
    )
    demand = DemandState(
        id=f"demand_{next_counter(world, CounterKind.DEMAND)}",
        vassalage_id=commitment.id,
        overlord_id=term.overlord_id,
        vassal_id=term.vassal_id,
        kind=order.demand_kind,
        amount=order.amount,
        granted=figures.granted,
        issued_turn=world.clock.turn,
        deadline_turn=world.clock.turn + scenario.tuning.vassal.demand_answer_turns,
    )
    world.vassal.demands.append(demand)
    world.vassal.last_demand_turn[commitment.id] = world.clock.turn
    raise_unrest(world, scenario, demand)
    return [
        diplomacy_event(
            DEMAND_ISSUED,
            [term.overlord_id, term.vassal_id],
            {"amount": demand.amount, "granted": demand.granted},
        )
    ]


def _find_demand(world: WorldState, demand_id: str) -> DemandState | None:
    return next((item for item in world.vassal.demands if item.id == demand_id), None)


def validate_answer_demand(world: WorldState, order: AnswerDemandOrder) -> None:
    demand = _find_demand(world, order.demand_id)
    if demand is None:
        raise _reject("unknown_demand")
    if demand.vassal_id != order.faction_id:
        raise _reject("not_vassal")
    if vassalage_by_id(world, demand.vassalage_id) is None:
        raise _reject("unknown_vassalage")
    if world.clock.turn > demand.deadline_turn:
        raise _reject("demand_expired")


def _answered_event(
    demand: DemandState, reply: DemandReply, reason_key: str
) -> EventLogEntry:
    event = diplomacy_event(DEMAND_ANSWERED, [demand.vassal_id, demand.overlord_id])
    summary = f"{DEMAND_ANSWERED}_{reply.value}_{reason_key}"
    event.cause = event.cause.model_copy(update={"summary_key": summary})
    return event


def _answer(
    world: WorldState,
    scenario: StrategyScenario,
    demand: DemandState,
    reply: DemandReply,
    reason_key: str,
) -> list[EventLogEntry]:
    world.vassal.demands = [
        item for item in world.vassal.demands if item.id != demand.id
    ]
    events = [_answered_event(demand, reply, reason_key)]
    return events + apply_reply(world, scenario, demand, reply)


def apply_answer_demand(
    world: WorldState, scenario: StrategyScenario, order: AnswerDemandOrder
) -> list[EventLogEntry]:
    demand = _find_demand(world, order.demand_id)
    assert demand is not None
    return _answer(world, scenario, demand, order.reply, "chosen")


def resolve_demands(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    due = [
        item
        for item in sorted(world.vassal.demands, key=lambda item: item.id)
        if item.deadline_turn <= world.clock.turn
    ]
    events: list[EventLogEntry] = []
    for demand in due:
        if vassalage_by_id(world, demand.vassalage_id) is None:
            world.vassal.demands.remove(demand)
            continue
        faction = world.factions[demand.vassal_id]
        if faction.is_player or faction.leader_id not in world.leaders:
            events += _answer(world, scenario, demand, DemandReply.REFUSE, "unanswered")
            continue
        choice = choose_reply(world, scenario, demand)
        events += _answer(world, scenario, demand, choice.reply, choice.reason_key)
    return events
