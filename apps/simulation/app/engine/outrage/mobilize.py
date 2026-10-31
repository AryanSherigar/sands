from app.engine.diplomacy.events import diplomacy_event
from app.engine.outrage.status import is_mobilized, outrage_of
from app.engine.pressure.wars import wars_of
from app.exceptions.command_exceptions import CommandError
from app.models.orders import MobilizeOrder
from app.models.world_diplomacy import OutrageState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import OutrageLevel

HTTP_UNPROCESSABLE = 422
MOBILIZATION_ORDERED = "mobilization_ordered"


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def validate_mobilize(
    world: WorldState, scenario: StrategyScenario, order: MobilizeOrder
) -> None:
    if world.outrage_ruleset < 1 or not scenario.toggles.is_outrage_enabled:
        raise _reject("outrage_disabled")
    if not wars_of(world, order.faction_id):
        raise _reject("not_at_war")
    if is_mobilized(world, order.faction_id):
        raise _reject("already_mobilized")


def apply_mobilize(
    world: WorldState, scenario: StrategyScenario, order: MobilizeOrder
) -> list[EventLogEntry]:
    until = world.clock.turn + scenario.tuning.outrage.mobilization_turns
    state = outrage_of(world, order.faction_id)
    if state is None:
        state = OutrageState(
            faction_id=order.faction_id, level=OutrageLevel.NONE, expires_turn=0
        )
        world.outrage.append(state)
        world.outrage.sort(key=lambda item: item.faction_id)
    state.mobilized_until_turn = until
    return [diplomacy_event(MOBILIZATION_ORDERED, [order.faction_id], {"until": until})]
