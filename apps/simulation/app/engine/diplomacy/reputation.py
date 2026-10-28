from app.models.world_faction import FactionState

MAX_PERCENT = 100


def shift_standing(faction: FactionState, reputation: int, stability: int) -> None:
    faction.reputation = min(
        MAX_PERCENT, max(-MAX_PERCENT, faction.reputation + reputation)
    )
    faction.stability = min(MAX_PERCENT, max(0, faction.stability + stability))
