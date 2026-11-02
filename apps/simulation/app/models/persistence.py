from datetime import datetime
from uuid import UUID

from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import SceneOutcome, ScenePackage, SceneStatus, SceneType
from strategy_contracts.terms import TermsCard
from strategy_contracts.treaty import Verdict, WeightBand


class PlaythroughRow(WorldModel):
    playthrough_id: UUID
    owner_user_id: UUID
    scenario: StrategyScenario
    scenario_schema_version: int
    created_at: datetime


class WorldStateRow(WorldModel):
    playthrough_id: UUID
    row_version: int
    schema_version: int
    turn: int
    world_hash: str
    document: dict[str, object]
    updated_at: datetime


class SceneExchangeRow(WorldModel):
    scene_id: UUID
    sequence: int
    player_text: str
    leader_text: str
    proposal: TermsCard | None
    cited_grudge_ids: list[str] = Field(default_factory=list)
    verdict: Verdict | None = None
    clause_bands: list[WeightBand] = Field(default_factory=list)
    created_at: datetime


class SnapshotRow(WorldModel):
    playthrough_id: UUID
    turn: int
    schema_version: int
    world_hash: str
    document: dict[str, object]
    created_at: datetime


class TurnHashRow(WorldModel):
    playthrough_id: UUID
    turn: int
    world_hash: str


class SceneRow(WorldModel):
    scene_id: UUID
    playthrough_id: UUID
    scene_type: SceneType
    status: SceneStatus
    turn: int
    package: ScenePackage
    outcome: SceneOutcome | None
    created_at: datetime
    resolved_at: datetime | None
    failed_attempts: int = 0
