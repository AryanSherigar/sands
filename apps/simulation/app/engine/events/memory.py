from app.models.world_event_memory import EventMemory
from app.models.world_state import WorldState
from strategy_contracts.limits import MAX_SCAR_POINTS


def find_memory(
    world: WorldState, template_id: str, subject_id: str
) -> EventMemory | None:
    return next(
        (
            memory
            for memory in world.event_memories
            if memory.template_id == template_id and memory.subject_id == subject_id
        ),
        None,
    )


def record_firing(
    world: WorldState, template_id: str, subject_id: str, tier: int
) -> None:
    memory = find_memory(world, template_id, subject_id)
    if memory is None:
        memory = EventMemory(template_id=template_id, subject_id=subject_id)
        world.event_memories.append(memory)
    memory.last_tier = tier
    memory.calm_turns = 0


def add_scar(world: WorldState, template_id: str, subject_id: str, points: int) -> None:
    if points <= 0:
        return
    memory = find_memory(world, template_id, subject_id)
    if memory is None:
        memory = EventMemory(template_id=template_id, subject_id=subject_id)
        world.event_memories.append(memory)
    memory.scar = min(memory.scar + points, MAX_SCAR_POINTS)
