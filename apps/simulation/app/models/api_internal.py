from uuid import UUID

from app.models.base import WorldModel
from app.models.world_player import PlayerRuler
from strategy_contracts.ids import WholeNumber
from strategy_contracts.scenario import StrategyScenario


class InitWorldRequest(WorldModel):
    playthrough_id: UUID
    owner_user_id: UUID
    scenario: StrategyScenario
    ruler: PlayerRuler
    seed: int


class InitWorldResponse(WorldModel):
    playthrough_id: UUID
    world_hash: str
    turn: WholeNumber
