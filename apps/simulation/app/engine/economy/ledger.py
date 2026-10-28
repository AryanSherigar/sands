from app.models.world_events import StateChange
from app.models.world_faction import FactionState


def change_treasury(faction: FactionState, delta: int) -> StateChange:
    before = faction.treasury
    faction.treasury = before + delta
    return StateChange(
        path=f"factions.{faction.id}.treasury", before=before, after=faction.treasury
    )


def available_cash(faction: FactionState) -> int:
    return max(0, faction.treasury)
