from app.models.api_world_view import WorldView
from app.models.base import WorldModel


class HistoricalWorldResponse(WorldModel):
    turn: int
    world_hash: str
    world: WorldView


class ReplayVerificationResponse(WorldModel):
    verified_turn: int
    world_hash: str
    step_count: int
