from typing import Literal
from uuid import UUID

from app.models.api_world_view import SceneRef
from app.models.base import WorldModel
from app.models.world_battle import BattleOutcome, BattleSide
from app.models.world_events import EventCause, TurnStatus
from pydantic import Field
from strategy_contracts.enums import TroopType
from strategy_contracts.ids import EntityId, RegionId, WholeNumber


class EndTurnResponse(WorldModel):
    status: TurnStatus
    turn: WholeNumber
    pending_scene: SceneRef | None = None


EconomyCategory = Literal["tax", "upkeep", "loan", "other"]


class ReportLine(WorldModel):
    text_key: str
    kind: str = ""
    subject_ids: list[EntityId] = Field(default_factory=list)
    cause: EventCause


class EconomyReportLine(WorldModel):
    kind: str
    category: EconomyCategory
    amount: int
    subject_ids: list[EntityId] = Field(default_factory=list)
    inputs: dict[str, int] = Field(default_factory=dict)


class BattleRoundReport(WorldModel):
    total_exchange: int
    own_losses: WholeNumber


class BattleReport(WorldModel):
    battle_id: str
    region_id: RegionId
    outcome: BattleOutcome | None
    own_side: BattleSide
    exchanges: int
    own_losses: dict[TroopType, WholeNumber] = Field(default_factory=dict)
    rounds: list[BattleRoundReport] = Field(default_factory=list)


class TurnReport(WorldModel):
    turn: WholeNumber
    net_gold: int = 0
    economy: list[EconomyReportLine] = Field(default_factory=list)
    battles: list[BattleReport] = Field(default_factory=list)
    lines: list[ReportLine] = Field(default_factory=list)
    major_event_kinds: list[str] = Field(default_factory=list)


class EventChoiceRequest(WorldModel):
    choice_id: EntityId


class BattlePlanRequest(WorldModel):
    formation: dict[str, WholeNumber]
    tactic: str


class BattleDeclineResponse(WorldModel):
    auto_resolved: bool


class ChronicleRequestResponse(WorldModel):
    scene_id: UUID
