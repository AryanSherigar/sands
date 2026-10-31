from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.engine.pressure.agents import generate_agent
from app.engine.rng import DeterministicRng
from app.models.orders import SendEnvoyOrder
from app.models.world_diplomacy import EnvoyState
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.scenario import StrategyScenario


def open_envoy(
    world: WorldState,
    order: SendEnvoyOrder,
    scenario: StrategyScenario,
    rng: DeterministicRng,
) -> EventLogEntry:
    envoy = EnvoyState(
        id=f"envoy_{next_counter(world, CounterKind.ENVOY)}",
        from_faction_id=order.faction_id,
        at_faction_id=order.target_faction_id,
    )
    if scenario.tuning.agents.is_enabled:
        envoy.agent = generate_agent(scenario, rng, envoy.id)
    world.envoys.append(envoy)
    return diplomacy_event(
        "envoy_sent", [envoy.id, order.faction_id, order.target_faction_id]
    )
