"""Request shapes for the simulation service's internal API."""

import uuid

from pydantic import BaseModel, ConfigDict, Field
from strategy_contracts.ids import AmbitionId, TraitId
from strategy_contracts.scenario import StrategyScenario


class PlayerRulerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    epithet: str | None = None
    portrait_url: str | None = None
    trait_ids: list[TraitId]
    ambition_ids: list[AmbitionId]
    backstory: str = ""


class InitializeCampaignRequest(BaseModel):
    """The seed is deliberately absent: the simulation service owns it."""

    model_config = ConfigDict(extra="forbid")

    playthrough_id: uuid.UUID
    owner_user_id: uuid.UUID
    operation_id: str = Field(min_length=1, max_length=128)
    scenario: StrategyScenario
    ruler: PlayerRulerRequest
    player_faction_id: str
