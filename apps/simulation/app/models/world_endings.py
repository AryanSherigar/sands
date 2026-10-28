from app.models.base import WorldModel
from strategy_contracts.ids import WholeNumber


class EndingsWorldState(WorldModel):
    regime_fall_turns: WholeNumber = 0
    hegemony_turns: WholeNumber = 0
    has_seen_war: bool = False
