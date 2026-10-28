from app.engine.events.lookup import find_template
from app.engine.events.tiers import tier_level
from app.engine.subjects import Subject
from app.models.world_event_memory import EventMemory
from app.models.world_state import WorldState
from strategy_contracts.events import EventDefinition
from strategy_contracts.scenario import StrategyScenario


def decay_memories(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> None:
    """Calm turns step a remembered tier down one level; scars fade every turn."""
    kept: list[EventMemory] = []
    for memory in world.event_memories:
        template = find_template(scenario, memory.template_id)
        if template is None:
            continue
        _decay_tier(world, template, memory, faction_id)
        memory.scar = max(0, memory.scar - template.scar.decay_per_turn)
        if memory.last_tier or memory.scar:
            kept.append(memory)
    world.event_memories = kept


def _decay_tier(
    world: WorldState,
    template: EventDefinition,
    memory: EventMemory,
    faction_id: str,
) -> None:
    subject = Subject(template.subject_kind, memory.subject_id)
    current = tier_level(world, template, subject, scar=0, faction_id=faction_id)
    if current >= memory.last_tier:
        memory.calm_turns = 0
        return
    memory.calm_turns += 1
    if memory.calm_turns >= template.tier_calm_turns:
        memory.last_tier = max(current, memory.last_tier - 1)
        memory.calm_turns = 0
