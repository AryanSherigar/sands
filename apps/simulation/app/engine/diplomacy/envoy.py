from app.engine.diplomacy.counters import next_counter
from app.engine.diplomacy.events import diplomacy_event
from app.models.orders import SendEnvoyOrder
from app.models.world_diplomacy import EnvoyState
from app.models.world_events import EventLogEntry
from app.models.world_state import CounterKind, WorldState


def open_envoy(world: WorldState, order: SendEnvoyOrder) -> EventLogEntry:
    envoy = EnvoyState(
        id=f"envoy_{next_counter(world, CounterKind.ENVOY)}",
        from_faction_id=order.faction_id,
        at_faction_id=order.target_faction_id,
    )
    world.envoys.append(envoy)
    return diplomacy_event(
        "envoy_sent", [envoy.id, order.faction_id, order.target_faction_id]
    )
