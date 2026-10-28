from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.internal import events
from app.engine.internal.rebel_armies import disperse_rebel_army
from app.models.world_events import EventLogEntry
from app.models.world_internal import (
    STAGE_ORDER,
    UprisingArchetype,
    UprisingStage,
    UprisingState,
)
from app.models.world_state import WorldState
from strategy_contracts.enums import TaxRate
from strategy_contracts.scenario import InternalTuning


def choose_archetype(
    world: WorldState, faction_id: str, unrest: int, tuning: InternalTuning
) -> UprisingArchetype:
    faction = world.factions[faction_id]
    if unrest >= PERCENT or faction.war_exhaustion >= tuning.rebellion_war_exhaustion:
        return UprisingArchetype.REBELLION
    if faction.tax_rate is TaxRate.HIGH:
        return UprisingArchetype.PETITION
    return UprisingArchetype.RIOT


def penalty_for_stage(base_percent: int, stage: UprisingStage, step: int) -> int:
    return clamp(base_percent + STAGE_ORDER.index(stage) * step, 0, PERCENT)


def apply_stage(uprising: UprisingState, stage: UprisingStage, step: int) -> None:
    offset = STAGE_ORDER.index(stage) - STAGE_ORDER.index(uprising.stage)
    uprising.stage = stage
    uprising.turns_in_stage = 0
    uprising.easing_turns = 0
    for field in (
        "income_penalty_percent",
        "manpower_penalty_percent",
        "supply_penalty_percent",
    ):
        current = getattr(uprising, field)
        setattr(uprising, field, clamp(current + offset * step, 0, PERCENT))


def is_garrisoned(world: WorldState, uprising: UprisingState) -> bool:
    region = world.regions[uprising.region_id]
    return region.garrison > 0 or any(
        army.owner_id == uprising.faction_id and army.location_id == region.id
        for army in world.armies.values()
    )


def is_easing(world: WorldState, uprising: UprisingState) -> bool:
    faction = world.factions[uprising.faction_id]
    return is_garrisoned(world, uprising) or faction.tax_rate is TaxRate.LOW


def advance_uprisings(world: WorldState, tuning: InternalTuning) -> list[EventLogEntry]:
    logged: list[EventLogEntry] = []
    for uprising in sorted(world.uprisings, key=lambda item: item.id):
        if uprising.started_turn == world.clock.turn:
            continue
        logged.extend(_advance(world, uprising, tuning))
    return logged


def _advance(
    world: WorldState, uprising: UprisingState, tuning: InternalTuning
) -> list[EventLogEntry]:
    if is_easing(world, uprising):
        return _ease(world, uprising, tuning)
    uprising.easing_turns = 0
    uprising.turns_in_stage += 1
    return _escalate(world, uprising, tuning)


def _ease(
    world: WorldState, uprising: UprisingState, tuning: InternalTuning
) -> list[EventLogEntry]:
    region = world.regions[uprising.region_id]
    if is_garrisoned(world, uprising):
        region.unrest = clamp(
            region.unrest - tuning.uprising_garrison_unrest_relief, 0, PERCENT
        )
    uprising.easing_turns += 1
    index = STAGE_ORDER.index(uprising.stage)
    if uprising.easing_turns < tuning.uprising_ease_after_turns or index == 0:
        return []
    before = uprising.stage
    apply_stage(
        uprising, STAGE_ORDER[index - 1], tuning.uprising_stage_penalty_step_percent
    )
    return [events.uprising_stage_changed(uprising, before)]


def _escalate(
    world: WorldState, uprising: UprisingState, tuning: InternalTuning
) -> list[EventLogEntry]:
    if uprising.stage is UprisingStage.ARMED:
        if uprising.turns_in_stage < tuning.uprising_armed_flip_turns:
            return []
        return [_flip_region(world, uprising)]
    if uprising.turns_in_stage < tuning.uprising_escalate_after_turns:
        return []
    before = uprising.stage
    index = STAGE_ORDER.index(before)
    apply_stage(
        uprising, STAGE_ORDER[index + 1], tuning.uprising_stage_penalty_step_percent
    )
    return [events.uprising_stage_changed(uprising, before)]


def _flip_region(world: WorldState, uprising: UprisingState) -> EventLogEntry:
    region = world.regions[uprising.region_id]
    previous_owner = region.owner_id
    region.owner_id = None
    region.occupation = None
    disperse_rebel_army(world, uprising.id)
    world.uprisings = [item for item in world.uprisings if item.id != uprising.id]
    world.uprising_cooldowns[region.id] = world.clock.turn
    return events.uprising_flipped(uprising, previous_owner)
