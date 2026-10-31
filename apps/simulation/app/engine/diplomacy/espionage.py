from app.engine.diplomacy.events import diplomacy_event
from app.engine.pressure.agents import bribe_price
from app.exceptions.command_exceptions import CommandError
from app.models.orders import BribeEnvoyOrder
from app.models.world_diplomacy import EnvoyState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario

HTTP_UNPROCESSABLE = 422


def _reject(reason: str) -> CommandError:
    return CommandError("order not possible", reason, HTTP_UNPROCESSABLE)


def _find_envoy(world: WorldState, envoy_id: str) -> EnvoyState:
    for envoy in world.envoys:
        if envoy.id == envoy_id:
            return envoy
    raise _reject("unknown_envoy")


def validate_bribe(
    world: WorldState, scenario: StrategyScenario, order: BribeEnvoyOrder
) -> None:
    if not scenario.tuning.agents.is_enabled:
        raise _reject("agents_disabled")
    envoy = _find_envoy(world, order.envoy_id)
    if envoy.from_faction_id == order.faction_id:
        raise _reject("own_envoy")
    if envoy.at_faction_id != order.faction_id:
        raise _reject("envoy_not_in_your_court")
    if envoy.agent is None:
        raise _reject("no_agent")
    if envoy.agent.bribed_by is not None:
        raise _reject("already_bribed")
    price = bribe_price(envoy.agent, scenario.tuning.agents)
    if world.factions[order.faction_id].treasury < price:
        raise _reject("cannot_afford_bribe")


def bribe_envoy(
    world: WorldState, scenario: StrategyScenario, order: BribeEnvoyOrder
) -> list[EventLogEntry]:
    envoy = _find_envoy(world, order.envoy_id)
    assert envoy.agent is not None
    world.factions[order.faction_id].treasury -= bribe_price(
        envoy.agent, scenario.tuning.agents
    )
    envoy.agent.bribed_by = order.faction_id
    return [diplomacy_event("envoy_bribed", [order.faction_id])]
