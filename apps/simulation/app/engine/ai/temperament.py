from app.engine.rng import derive_state
from strategy_contracts.stances import ScoreCategory

TEMPERAMENT_STREAM = "temperament"
TEMPERAMENT_SPAN = 5
TEMPERAMENT_FLOOR = -2


def temperament_bias(seed: int, leader_id: str, category: ScoreCategory) -> int:
    state = derive_state(seed, TEMPERAMENT_STREAM, leader_id, category.value)
    return state % TEMPERAMENT_SPAN + TEMPERAMENT_FLOOR
