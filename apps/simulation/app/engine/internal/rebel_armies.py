from app.engine.economy.armies import remove_army
from app.models.world_state import WorldState

REBEL_ARMY_PREFIX = "rebel"


def rebel_army_id(uprising_id: str) -> str:
    return f"{REBEL_ARMY_PREFIX}_{uprising_id}"


def disperse_rebel_army(world: WorldState, uprising_id: str) -> None:
    """An uprising that ends by any road takes its rebel army with it."""
    army_id = rebel_army_id(uprising_id)
    if army_id in world.armies:
        remove_army(world, army_id)
