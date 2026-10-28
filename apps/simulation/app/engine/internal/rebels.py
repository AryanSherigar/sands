from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.internal import events
from app.engine.internal.rebel_armies import rebel_army_id
from app.engine.internal.uprising_lifecycle import is_garrisoned
from app.models.world_army import ArmyState
from app.models.world_diplomacy import RelationState
from app.models.world_events import EventLogEntry
from app.models.world_faction import FactionState
from app.models.world_internal import (
    REBEL_FACTION_ID,
    UprisingStage,
    UprisingState,
)
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus, TaxRate, TroopType
from strategy_contracts.scenario import InternalTuning


def ensure_rebel_faction(world: WorldState) -> None:
    if REBEL_FACTION_ID in world.factions:
        return
    world.factions[REBEL_FACTION_ID] = FactionState(
        id=REBEL_FACTION_ID,
        leader_id=None,
        treasury=0,
        stability=PERCENT,
        war_exhaustion=0,
        reputation=0,
        tax_rate=TaxRate.NORMAL,
        orders_remaining=0,
        is_player=False,
    )
    for other_id in sorted(world.factions):
        if other_id == REBEL_FACTION_ID:
            continue
        low, high = sorted((other_id, REBEL_FACTION_ID))
        world.relations.append(
            RelationState(
                faction_a=low,
                faction_b=high,
                status=RelationStatus.WAR,
                since_turn=world.clock.turn,
            )
        )


def _troops_for(
    world: WorldState, uprising: UprisingState, tuning: InternalTuning
) -> int:
    population = world.regions[uprising.region_id].population
    share = population * tuning.rebel_army_population_percent // PERCENT
    return max(tuning.rebel_army_min_troops, share)


def _needs_army(world: WorldState, uprising: UprisingState) -> bool:
    return (
        uprising.stage is UprisingStage.ARMED
        and not uprising.has_rebel_army
        and not is_garrisoned(world, uprising)
    )


def raise_rebel_armies(
    world: WorldState, tuning: InternalTuning
) -> list[EventLogEntry]:
    logged: list[EventLogEntry] = []
    for uprising in sorted(world.uprisings, key=lambda item: item.id):
        if not _needs_army(world, uprising):
            continue
        ensure_rebel_faction(world)
        troops = _troops_for(world, uprising, tuning)
        army_id = rebel_army_id(uprising.id)
        world.armies[army_id] = ArmyState(
            id=army_id,
            owner_id=REBEL_FACTION_ID,
            troops={TroopType.INFANTRY: troops},
            morale=tuning.rebel_army_morale,
            location_id=uprising.region_id,
        )
        uprising.has_rebel_army = True
        logged.append(events.rebel_army_raised(uprising, army_id, troops))
    return logged


def end_crushed_uprisings(
    world: WorldState, tuning: InternalTuning
) -> list[EventLogEntry]:
    """An uprising whose rebel army has been destroyed is over; the region calms."""
    logged: list[EventLogEntry] = []
    for uprising in sorted(world.uprisings, key=lambda item: item.id):
        is_crushed = (
            uprising.has_rebel_army and rebel_army_id(uprising.id) not in world.armies
        )
        if is_crushed:
            logged.append(_crush(world, uprising, tuning))
    return logged


def _crush(
    world: WorldState, uprising: UprisingState, tuning: InternalTuning
) -> EventLogEntry:
    region = world.regions[uprising.region_id]
    faction = world.factions[uprising.faction_id]
    unrest_before = region.unrest
    region.unrest = clamp(unrest_before - tuning.crushed_unrest_reduction, 0, PERCENT)
    faction.stability = clamp(
        faction.stability + tuning.crushed_stability_gain, 0, PERCENT
    )
    world.uprisings = [item for item in world.uprisings if item.id != uprising.id]
    world.uprising_cooldowns[region.id] = world.clock.turn
    return events.uprising_crushed(uprising, unrest_before, region.unrest)
