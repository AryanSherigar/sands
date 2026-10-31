from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.pressure.wars import side_of
from app.exceptions.command_exceptions import CommandError
from app.models.orders import CutSubsidyOrder, SubsidizeOrder
from app.models.world_diplomacy import WarState
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_pressure import SubsidyState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

HTTP_UNPROCESSABLE = 422
SUBSIDY_GRANTED = "subsidy_granted"
SUBSIDY_CUT = "subsidy_cut"
SUBSIDY_PAID = "subsidy_paid"
SUBSIDY_DEFAULTED = "subsidy_defaulted"


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def _is_at_war(world: WorldState, first: FactionId, second: FactionId) -> bool:
    pair = tuple(sorted((first, second)))
    return any(
        (relation.faction_a, relation.faction_b) == pair
        and relation.status == RelationStatus.WAR
        for relation in world.relations
    )


def _require_receiver(world: WorldState, war: WarState, order: SubsidizeOrder) -> None:
    receiver = world.factions.get(order.target_faction_id)
    is_unavailable = (
        receiver is None
        or receiver.is_destroyed
        or receiver.leader_id is None
        or order.target_faction_id == order.faction_id
    )
    if is_unavailable:
        raise _reject("receiver_unavailable")
    receiver_side = side_of(war, order.target_faction_id)
    if receiver_side is None:
        raise _reject("receiver_not_in_war")
    payer_side = side_of(war, order.faction_id)
    is_opposed = payer_side is not None and payer_side != receiver_side
    if is_opposed or _is_at_war(world, order.faction_id, order.target_faction_id):
        raise _reject("payer_is_enemy")


def _require_terms(scenario: StrategyScenario, order: SubsidizeOrder) -> None:
    tuning = scenario.tuning.pressure
    if not 1 <= order.amount_per_turn <= tuning.subsidy_max_per_turn:
        raise _reject("bad_amount")
    if not 1 <= order.turns <= tuning.subsidy_max_turns:
        raise _reject("bad_duration")


def _find_subsidy(
    world: WorldState, payer_id: FactionId, receiver_id: FactionId, war_id: str
) -> SubsidyState | None:
    return next(
        (
            item
            for item in world.pressure.subsidies
            if (item.payer_id, item.receiver_id, item.war_id)
            == (payer_id, receiver_id, war_id)
        ),
        None,
    )


def validate_subsidize(
    world: WorldState, scenario: StrategyScenario, order: SubsidizeOrder
) -> None:
    if not world.pressure_ruleset:
        raise _reject("pressure_disabled")
    war = next((item for item in world.wars if item.id == order.war_id), None)
    if war is None:
        raise _reject("unknown_war")
    _require_receiver(world, war, order)
    _require_terms(scenario, order)
    if _find_subsidy(world, order.faction_id, order.target_faction_id, war.id):
        raise _reject("subsidy_exists")
    if world.factions[order.faction_id].treasury < order.amount_per_turn:
        raise _reject("cannot_pay")


def validate_cut_subsidy(world: WorldState, order: CutSubsidyOrder) -> None:
    subsidy = next(
        (item for item in world.pressure.subsidies if item.id == order.subsidy_id),
        None,
    )
    if subsidy is None:
        raise _reject("unknown_subsidy")
    if subsidy.payer_id != order.faction_id:
        raise _reject("not_payer")


def apply_subsidize(
    world: WorldState, scenario: StrategyScenario, order: SubsidizeOrder
) -> list[EventLogEntry]:
    subsidy = SubsidyState(
        id=f"subsidy_{next_counter(world, CounterKind.SUBSIDY)}",
        payer_id=order.faction_id,
        receiver_id=order.target_faction_id,
        war_id=order.war_id,
        amount_per_turn=order.amount_per_turn,
        expires_turn=world.clock.turn + order.turns - 1,
    )
    world.pressure.subsidies.append(subsidy)
    return [
        diplomacy_event(
            SUBSIDY_GRANTED,
            [subsidy.id, subsidy.payer_id, subsidy.receiver_id],
            {"amount_per_turn": subsidy.amount_per_turn, "turns": order.turns},
        )
    ]


def apply_cut_subsidy(world: WorldState, order: CutSubsidyOrder) -> list[EventLogEntry]:
    subsidy = next(
        item for item in world.pressure.subsidies if item.id == order.subsidy_id
    )
    world.pressure.subsidies.remove(subsidy)
    return [
        diplomacy_event(
            SUBSIDY_CUT, [subsidy.id, subsidy.payer_id, subsidy.receiver_id]
        )
    ]


def _is_unpayable(world: WorldState, subsidy: SubsidyState) -> bool:
    payer = world.factions[subsidy.payer_id]
    receiver = world.factions[subsidy.receiver_id]
    return (
        payer.is_destroyed
        or receiver.is_destroyed
        or payer.treasury < subsidy.amount_per_turn
    )


def pay_subsidies(world: WorldState) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    live = sorted(
        (
            item
            for item in world.pressure.subsidies
            if item.expires_turn >= world.clock.turn
        ),
        key=lambda item: item.id,
    )
    for subsidy in live:
        subjects = [subsidy.id, subsidy.payer_id, subsidy.receiver_id]
        if _is_unpayable(world, subsidy):
            world.pressure.subsidies.remove(subsidy)
            events.append(
                diplomacy_event(SUBSIDY_DEFAULTED, subjects, phase=PhaseName.TIME)
            )
            continue
        world.factions[subsidy.payer_id].treasury -= subsidy.amount_per_turn
        world.factions[subsidy.receiver_id].treasury += subsidy.amount_per_turn
        events.append(
            diplomacy_event(
                SUBSIDY_PAID,
                subjects,
                {"amount": subsidy.amount_per_turn},
                phase=PhaseName.TIME,
            )
        )
    return events
