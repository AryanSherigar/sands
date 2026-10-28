from app.models.world_faction import FactionState


def next_turn_orders(
    orders_per_turn: int, faction: FactionState, bonus: int = 0
) -> int:
    return max(0, orders_per_turn + bonus - faction.orders_debt)
