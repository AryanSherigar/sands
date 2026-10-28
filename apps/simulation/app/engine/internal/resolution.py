from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.internal import events
from app.engine.internal.rebel_armies import disperse_rebel_army
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import ResolveUprisingCommand
from app.models.world_events import EventLogEntry
from app.models.world_internal import (
    UprisingArchetype,
    UprisingResponse,
    UprisingState,
    allowed_responses,
)
from app.models.world_state import UPRISING_LIFECYCLE_RULESET, WorldState
from strategy_contracts.scenario import InternalTuning


def validate_resolution(world: WorldState, command: ResolveUprisingCommand) -> None:
    uprising = next(
        (item for item in world.uprisings if item.id == command.uprising_id), None
    )
    if uprising is None or uprising.faction_id != command.faction_id:
        raise CommandError("uprising unavailable", "not_found", 404)
    is_lifecycle = world.internal_ruleset >= UPRISING_LIFECYCLE_RULESET
    if is_lifecycle and command.response not in allowed_responses(uprising):
        raise CommandError("no one to answer the crowd", "no_spokesperson", 422)


def apply_resolution(
    world: WorldState, command: ResolveUprisingCommand, tuning: InternalTuning
) -> EventLogEntry:
    validate_resolution(world, command)
    uprising = next(item for item in world.uprisings if item.id == command.uprising_id)
    region = world.regions[uprising.region_id]
    faction = world.factions[command.faction_id]
    unrest_before, stability_before = region.unrest, faction.stability
    unrest_change, stability_change = _response_changes(command.response, tuning)
    region.unrest = clamp(region.unrest + unrest_change, 0, PERCENT)
    faction.stability = clamp(faction.stability + stability_change, 0, PERCENT)
    if world.internal_ruleset >= UPRISING_LIFECYCLE_RULESET:
        _apply_costs(world, uprising, command.response, tuning)
    disperse_rebel_army(world, uprising.id)
    world.uprisings = [item for item in world.uprisings if item.id != uprising.id]
    world.uprising_cooldowns[region.id] = world.clock.turn
    return events.uprising_resolved(
        uprising.id,
        faction.id,
        region.id,
        command.response.value,
        unrest_before,
        region.unrest,
        stability_before,
        faction.stability,
    )


def _apply_costs(
    world: WorldState,
    uprising: UprisingState,
    response: UprisingResponse,
    tuning: InternalTuning,
) -> None:
    if response is UprisingResponse.CONCESSIONS:
        _apply_concession_costs(world, uprising, tuning)
    elif response is UprisingResponse.RESTORE_ORDER:
        expires = world.clock.turn + tuning.restore_order_grudge_turns
        world.region_grudges[uprising.region_id] = expires


def _apply_concession_costs(
    world: WorldState, uprising: UprisingState, tuning: InternalTuning
) -> None:
    faction = world.factions[uprising.faction_id]
    cost = tuning.concessions_reputation_cost
    if uprising.archetype is UprisingArchetype.REBELLION:
        cost *= tuning.rebellion_concessions_cost_multiplier
    faction.reputation = clamp(faction.reputation - cost, -PERCENT, PERCENT)
    for region_id, region in sorted(world.regions.items()):
        is_precedent_target = (
            region.owner_id == faction.id
            and region_id != uprising.region_id
            and region.unrest >= tuning.precedent_unrest_threshold
        )
        if is_precedent_target:
            region.unrest = clamp(region.unrest + tuning.precedent_unrest, 0, PERCENT)


def _response_changes(
    response: UprisingResponse, tuning: InternalTuning
) -> tuple[int, int]:
    if response is UprisingResponse.CONCESSIONS:
        return -tuning.concessions_unrest_reduction, tuning.concessions_stability_gain
    if response is UprisingResponse.RESTORE_ORDER:
        return (
            -tuning.restore_order_unrest_reduction,
            -tuning.restore_order_stability_loss,
        )
    return -tuning.negotiate_unrest_reduction, 0
