from app.models.base import WorldModel
from strategy_contracts.ids import FactionId, LeaderId, WholeNumber
from strategy_contracts.stances import ScoreCategory


class AimState(WorldModel):
    category: ScoreCategory
    target_faction_id: FactionId | None = None
    chosen_turn: WholeNumber
    leader_id: LeaderId
    stance_option_id: str | None = None
    capital_held: bool
