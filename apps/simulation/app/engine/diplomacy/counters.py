from app.models.world_state import CounterKind, WorldState


def next_counter(world: WorldState, kind: CounterKind) -> int:
    count = world.counters.get(kind, 0) + 1
    world.counters[kind] = count
    return count
