from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import FactionId, RegionId, WholeNumber
from strategy_contracts.vassal import ConsentAction, DemandKind


class DemandState(WorldModel):
    id: str
    vassalage_id: str
    overlord_id: FactionId
    vassal_id: FactionId
    kind: DemandKind
    amount: WholeNumber
    granted: WholeNumber
    issued_turn: WholeNumber
    deadline_turn: WholeNumber


class ConsentState(WorldModel):
    vassalage_id: str
    action: ConsentAction
    target_faction_id: FactionId
    expires_turn: WholeNumber


class VassalStanding(WorldModel):
    vassalage_id: str
    grievance: WholeNumber = 0


class AnnexationRecord(WorldModel):
    turn: WholeNumber
    overlord_id: FactionId
    vassal_id: FactionId
    region_ids: list[RegionId] = Field(default_factory=list)
    wealth: WholeNumber = 0


class VassalWorldState(WorldModel):
    demands: list[DemandState] = Field(default_factory=list)
    consents: list[ConsentState] = Field(default_factory=list)
    standing: list[VassalStanding] = Field(default_factory=list)
    last_demand_turn: dict[str, WholeNumber] = Field(default_factory=dict)
    garrison_until: dict[str, WholeNumber] = Field(default_factory=dict)
    annexations: list[AnnexationRecord] = Field(default_factory=list)
    independence_wars: dict[str, str] = Field(default_factory=dict)
