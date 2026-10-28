from enum import Enum

from app.models.base import WorldModel
from app.models.world_diplomacy import WarSide
from pydantic import Field, SerializerFunctionWrapHandler, model_serializer
from strategy_contracts.ids import FactionId, WholeNumber


class CallKind(str, Enum):
    ALLIANCE = "alliance"
    LEVY = "levy"
    PROTECTION = "protection"


class CallToArmsState(WorldModel):
    id: str
    alliance_id: str
    war_id: str
    caller_id: FactionId
    ally_id: FactionId
    side: WarSide
    issued_turn: WholeNumber
    deadline_turn: WholeNumber
    is_defensive: bool
    kind: CallKind = CallKind.ALLIANCE

    @model_serializer(mode="wrap")
    def omit_alliance_kind(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        if document.get("kind") == CallKind.ALLIANCE.value:
            document.pop("kind", None)
        return document


class AllianceStanding(WorldModel):
    alliance_id: str
    refusals_by_faction: dict[FactionId, WholeNumber] = Field(default_factory=dict)


class AllianceWorldState(WorldModel):
    calls: list[CallToArmsState] = Field(default_factory=list)
    standing: list[AllianceStanding] = Field(default_factory=list)
