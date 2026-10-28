"""Campaign initialization schema and models."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.base import WorldModel
from app.models.world_player import PlayerRuler
from strategy_contracts.scenario import StrategyScenario


class InitializeCampaign(WorldModel):
    """Schema for initializing a campaign playthrough from scenario definition and seed."""

    playthrough_id: UUID
    owner_user_id: UUID
    operation_id: str = Field(min_length=1, max_length=128)
    scenario: StrategyScenario
    ruler: PlayerRuler
    seed: int | None = None
    player_faction_id: str


CampaignStatus = Literal[
    "planning",
    "awaiting_commands",
    "awaiting_battle_decision",
    "awaiting_scene",
    "turn_completed",
]


__all__ = [
    "InitializeCampaign",
    "CampaignStatus",
    "PlayerRuler",
]
