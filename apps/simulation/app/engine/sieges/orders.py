from app.engine.diplomacy.validation import is_at_war
from app.engine.movement.engagement import armies_in_open_battle
from app.engine.sieges.events import siege_started
from app.engine.sieges.presence import armies_at
from app.exceptions.command_exceptions import CommandError
from app.models.orders import BesiegeOrder
from app.models.world_events import EventLogEntry
from app.models.world_siege import SiegeState
from app.models.world_state import WorldState

HTTP_UNPROCESSABLE = 422


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def validate_besiege(world: WorldState, command: BesiegeOrder) -> None:
    if world.siege_ruleset < 1:
        raise _reject("siege_not_enabled")
    army = world.armies.get(command.army_id)
    if army is None or army.owner_id != command.faction_id:
        raise _reject("not_your_army")
    if army.location_id != command.target_region_id:
        raise _reject("wrong_region")
    if command.army_id in armies_in_open_battle(world):
        raise _reject("army_in_battle")
    _validate_target(world, command)


def _validate_target(world: WorldState, command: BesiegeOrder) -> None:
    region = world.regions[command.target_region_id]
    if region.owner_id is None:
        raise _reject("no_owner")
    if region.owner_id == command.faction_id:
        raise _reject("own_region")
    if not is_at_war(world, command.faction_id, region.owner_id):
        raise _reject("not_at_war")
    if region.occupation is not None:
        raise _reject("already_occupied")
    siege = find_siege(world, command.target_region_id)
    if siege is not None and siege.besieger_id != command.faction_id:
        raise _reject("already_besieged")


def find_siege(world: WorldState, region_id: str) -> SiegeState | None:
    return next((item for item in world.sieges if item.region_id == region_id), None)


def apply_besiege(world: WorldState, command: BesiegeOrder) -> list[EventLogEntry]:
    army_ids = armies_at(world, command.faction_id, command.target_region_id)
    siege = find_siege(world, command.target_region_id)
    if siege is not None:
        siege.army_ids = army_ids
        return []
    world.sieges.append(
        SiegeState(
            region_id=command.target_region_id,
            besieger_id=command.faction_id,
            army_ids=army_ids,
        )
    )
    return [siege_started(command.faction_id, command.target_region_id, army_ids)]
