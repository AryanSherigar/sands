from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import EntityId, FactionId, RegionId, WholeNumber
from strategy_contracts.pressure import HopeSource, PressureBand, RumorTopic, ShockKind


class ShockRecord(WorldModel):
    war_id: str
    faction_id: FactionId
    kind: ShockKind
    turn: WholeNumber


class MediationOffer(WorldModel):
    id: str
    mediator_id: FactionId
    war_id: str
    expires_turn: WholeNumber


class SubsidyState(WorldModel):
    id: str
    payer_id: FactionId
    receiver_id: FactionId
    war_id: str
    expires_turn: WholeNumber


class RumorState(WorldModel):
    id: str
    observer_id: FactionId
    about_faction_id: FactionId
    envoy_id: EntityId
    topic: RumorTopic
    band: PressureBand
    line_key: str
    turn: WholeNumber
    is_hint_wrong: bool = False


class PressureState(WorldModel):
    stalemate_turns: dict[str, WholeNumber] = Field(default_factory=dict)
    humiliation: dict[FactionId, WholeNumber] = Field(default_factory=dict)
    devastation: dict[RegionId, WholeNumber] = Field(default_factory=dict)
    shocks: list[ShockRecord] = Field(default_factory=list)
    mediation_offers: list[MediationOffer] = Field(default_factory=list)
    subsidies: list[SubsidyState] = Field(default_factory=list)
    rumors: list[RumorState] = Field(default_factory=list)
    last_bands: dict[FactionId, str] = Field(default_factory=dict)


class StrainReading(WorldModel):
    value: WholeNumber
    factors: dict[str, int] = Field(default_factory=dict)


class HopeReading(WorldModel):
    sources: list[HopeSource] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    bonus: WholeNumber = 0


class WillReading(WorldModel):
    value: WholeNumber
    floor: WholeNumber = 0
    factors: dict[str, int] = Field(default_factory=dict)
