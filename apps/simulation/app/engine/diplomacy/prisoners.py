from app.engine.coalitions.ledger import record_atrocity
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.reputation import shift_standing
from app.engine.peace.hostages import find_hostage, harm_hostage, release_hostage
from app.engine.pressure.wars import find_war
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.peace import PeaceTuning
from strategy_contracts.scenario import StrategyScenario

PRISONER_RELEASED = "prisoner_released"
PRISONER_RANSOMED = "prisoner_ransomed"
PRISONER_EXCHANGED = "prisoner_exchanged"
PRISONER_EXECUTED = "prisoner_executed"
EXCHANGE_TROOP_TOLERANCE = 1


def ransom_price(prisoner: PrisonerState, tuning: PeaceTuning) -> int:
    if prisoner.kind == PrisonerKind.CHARACTER:
        return tuning.ransom_gold_per_character
    return prisoner.troop_count * tuning.ransom_gold_per_troop


def find_prisoner(world: WorldState, prisoner_id: str) -> PrisonerState | None:
    return next((item for item in world.prisoners if item.id == prisoner_id), None)


def find_exchange_counterpart(
    world: WorldState, prisoner: PrisonerState
) -> PrisonerState | None:
    candidates = [
        item
        for item in sorted(world.prisoners, key=lambda entry: entry.id)
        if item.held_by_id == prisoner.origin_faction_id
        and item.origin_faction_id == prisoner.held_by_id
        and item.kind == prisoner.kind
        and abs(item.troop_count - prisoner.troop_count) <= EXCHANGE_TROOP_TOLERANCE
    ]
    return candidates[0] if candidates else None


def free_prisoner(world: WorldState, prisoner: PrisonerState) -> None:
    world.prisoners = [item for item in world.prisoners if item.id != prisoner.id]
    capital_id = world.factions[prisoner.origin_faction_id].capital_region_id
    if prisoner.kind == PrisonerKind.TROOPS and capital_id in world.regions:
        world.regions[capital_id].manpower += prisoner.troop_count


def _add_chip(
    world: WorldState, faction_id: FactionId, opponent_id: FactionId, chip: int
) -> None:
    war = find_war(world, faction_id, opponent_id)
    if war is None or chip == 0:
        return
    key = f"{war.id}:{faction_id}"
    world.peace.ransom_points[key] = world.peace.ransom_points.get(key, 0) + chip


def _ransom(
    world: WorldState, tuning: PeaceTuning, prisoner: PrisonerState
) -> list[EventLogEntry]:
    price = min(
        ransom_price(prisoner, tuning),
        world.factions[prisoner.origin_faction_id].treasury,
    )
    world.factions[prisoner.origin_faction_id].treasury -= price
    world.factions[prisoner.held_by_id].treasury += price
    free_prisoner(world, prisoner)
    _add_chip(
        world, prisoner.held_by_id, prisoner.origin_faction_id, tuning.ransom_score_chip
    )
    return [
        diplomacy_event(
            PRISONER_RANSOMED,
            [prisoner.id, prisoner.held_by_id, prisoner.origin_faction_id],
            {"gold": price},
        )
    ]


def _exchange(
    world: WorldState, tuning: PeaceTuning, prisoner: PrisonerState
) -> list[EventLogEntry]:
    counterpart = find_exchange_counterpart(world, prisoner)
    assert counterpart is not None
    holder_id, origin_id = prisoner.held_by_id, prisoner.origin_faction_id
    free_prisoner(world, prisoner)
    free_prisoner(world, counterpart)
    _add_chip(world, holder_id, origin_id, tuning.exchange_score_chip)
    _add_chip(world, origin_id, holder_id, tuning.exchange_score_chip)
    return [
        diplomacy_event(
            PRISONER_EXCHANGED, [prisoner.id, counterpart.id, holder_id, origin_id]
        )
    ]


def _release(world: WorldState, prisoner: PrisonerState) -> list[EventLogEntry]:
    free_prisoner(world, prisoner)
    return [
        diplomacy_event(
            PRISONER_RELEASED,
            [prisoner.id, prisoner.held_by_id, prisoner.origin_faction_id],
        )
    ]


def _execute(
    world: WorldState, tuning: PeaceTuning, prisoner: PrisonerState
) -> list[EventLogEntry]:
    world.prisoners = [item for item in world.prisoners if item.id != prisoner.id]
    shift_standing(
        world.factions[prisoner.held_by_id], -tuning.atrocity_reputation_cost, 0
    )
    record_atrocity(world, prisoner.held_by_id)
    return [
        diplomacy_event(
            PRISONER_EXECUTED,
            [prisoner.id, prisoner.held_by_id, prisoner.origin_faction_id],
        )
    ]


def _handle_hostage(
    world: WorldState, scenario: StrategyScenario, order: HandlePrisonerOrder
) -> list[EventLogEntry]:
    if order.action == "execute":
        return harm_hostage(world, scenario, order.prisoner_id, order.faction_id)
    return release_hostage(world, order.prisoner_id)


def handle_prisoner(
    world: WorldState, scenario: StrategyScenario, order: HandlePrisonerOrder
) -> list[EventLogEntry]:
    """Apply a validated prisoner order; callers run `validate_prisoner_order` first."""
    if find_hostage(world, order.prisoner_id) is not None:
        return _handle_hostage(world, scenario, order)
    prisoner = find_prisoner(world, order.prisoner_id)
    assert prisoner is not None
    tuning = scenario.tuning.peace
    if order.action == "ransom":
        return _ransom(world, tuning, prisoner)
    if order.action == "exchange":
        return _exchange(world, tuning, prisoner)
    if order.action == "release":
        return _release(world, prisoner)
    return _execute(world, tuning, prisoner)
