from app.models.api_world_view import WorldView
from app.models.base import WorldModel
from app.models.battle_progress import CampaignState
from app.models.world_battle import BattleView, ExchangeReport
from pydantic import Field


class CampaignWorldView(WorldView, CampaignState):
    pass


class BattlePage(WorldModel):
    world_version: int
    items: list[BattleView] = Field(default_factory=list)
    next_after_id: str | None = None


class ExchangeReportPage(WorldModel):
    items: list[ExchangeReport] = Field(default_factory=list)
    next_after_exchange: int | None = None
