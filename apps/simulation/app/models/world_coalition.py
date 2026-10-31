from app.models.base import WorldModel
from pydantic import Field, SerializerFunctionWrapHandler, model_serializer
from strategy_contracts.ids import FactionId, WholeNumber


class ConquestRecord(WorldModel):
    turn: WholeNumber
    faction_id: FactionId
    wealth: WholeNumber


class CoalitionState(WorldModel):
    id: str
    target_id: FactionId
    member_ids: list[FactionId] = Field(default_factory=list)
    formed_turn: WholeNumber
    expires_turn: WholeNumber


class CoalitionWorldState(WorldModel):
    coalitions: list[CoalitionState] = Field(default_factory=list)
    conquests: list[ConquestRecord] = Field(default_factory=list)
    atrocities: dict[FactionId, WholeNumber] = Field(default_factory=dict)
    appease_cooldowns: dict[str, WholeNumber] = Field(default_factory=dict)
    rejoin_lockouts: dict[str, WholeNumber] = Field(default_factory=dict)

    @model_serializer(mode="wrap")
    def omit_empty_appease_state(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        document = handler(self)
        for key in ("appease_cooldowns", "rejoin_lockouts"):
            if not document.get(key):
                document.pop(key, None)
        return document


def pair_key(target_id: FactionId, member_id: FactionId) -> str:
    return f"{target_id}:{member_id}"
