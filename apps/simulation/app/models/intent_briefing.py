from app.models.base import WorldModel
from app.models.world_battle import BattleView
from strategy_contracts.battle import Tactic


class IntentBriefing(WorldModel):
    battle: BattleView
    faction_id: str
    orders_remaining: int
    treasury: int
    legal_tactics: list[Tactic]
    capture_ids: list[str]
