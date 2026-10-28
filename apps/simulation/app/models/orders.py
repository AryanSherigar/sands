from typing import Annotated, Literal

from app.models.base import WorldModel
from pydantic import Field, model_validator
from strategy_contracts.enums import (
    ImprovementKind,
    PayLevel,
    RouteStyle,
    TaxRate,
    TroopType,
)
from strategy_contracts.ids import (
    ArmyId,
    EntityId,
    FactionId,
    RegionId,
    WholeNumber,
)
from strategy_contracts.terms import Term
from strategy_contracts.vassal import ConsentAction, DemandKind, DemandReply

MIN_ARMIES_TO_MERGE = 2
MAX_VIA_REGIONS = 3
MAX_AVOID_REGIONS = 5


class MoveArmyOrder(WorldModel):
    kind: Literal["move_army"] = "move_army"
    faction_id: FactionId
    army_id: ArmyId
    to_region_id: RegionId
    route_style: RouteStyle = RouteStyle.FASTEST
    via_region_ids: list[RegionId] = Field(
        default_factory=list, max_length=MAX_VIA_REGIONS
    )
    avoid_region_ids: list[RegionId] = Field(
        default_factory=list, max_length=MAX_AVOID_REGIONS
    )

    @model_validator(mode="after")
    def validate_route_choices(self) -> "MoveArmyOrder":
        for regions in (self.via_region_ids, self.avoid_region_ids):
            if len(set(regions)) != len(regions):
                raise ValueError("route regions may not repeat")
        if set(self.via_region_ids) & set(self.avoid_region_ids):
            raise ValueError("a region cannot be both via and avoid")
        return self


class HaltArmyOrder(WorldModel):
    kind: Literal["halt_army"] = "halt_army"
    faction_id: FactionId
    army_id: ArmyId


class AttackOrder(WorldModel):
    kind: Literal["attack"] = "attack"
    faction_id: FactionId
    army_id: ArmyId
    target_region_id: RegionId


class MapScoutOrder(WorldModel):
    kind: Literal["map_scout"] = "map_scout"
    faction_id: FactionId
    target_region_id: RegionId


class BesiegeOrder(WorldModel):
    kind: Literal["besiege"] = "besiege"
    faction_id: FactionId
    army_id: ArmyId


class RaiseArmyOrder(WorldModel):
    kind: Literal["raise_army"] = "raise_army"
    faction_id: FactionId
    region_id: RegionId
    troops: dict[TroopType, WholeNumber]


class DisbandArmyOrder(WorldModel):
    kind: Literal["disband_army"] = "disband_army"
    faction_id: FactionId
    army_id: ArmyId


class MergeArmiesOrder(WorldModel):
    kind: Literal["merge_armies"] = "merge_armies"
    faction_id: FactionId
    army_ids: list[ArmyId] = Field(min_length=MIN_ARMIES_TO_MERGE)
    into_army_id: ArmyId


class SplitArmyOrder(WorldModel):
    kind: Literal["split_army"] = "split_army"
    faction_id: FactionId
    army_id: ArmyId
    troops: dict[TroopType, WholeNumber]


class SetPayOrder(WorldModel):
    kind: Literal["set_pay"] = "set_pay"
    faction_id: FactionId
    army_id: ArmyId
    pay_level: PayLevel


class SetTaxRateOrder(WorldModel):
    kind: Literal["set_tax_rate"] = "set_tax_rate"
    faction_id: FactionId
    tax_rate: TaxRate


class TakeLoanOrder(WorldModel):
    kind: Literal["take_loan"] = "take_loan"
    faction_id: FactionId
    amount: int


class DeclareDefaultOrder(WorldModel):
    kind: Literal["declare_default"] = "declare_default"
    faction_id: FactionId


class BuildImprovementOrder(WorldModel):
    kind: Literal["build_improvement"] = "build_improvement"
    faction_id: FactionId
    region_id: RegionId
    improvement_kind: ImprovementKind


class DiplomaticPlayOrder(WorldModel):
    kind: Literal["diplomatic_play"] = "diplomatic_play"
    faction_id: FactionId
    target_faction_id: FactionId
    demands: list[Term] = Field(default_factory=list)


class DeclareWarOrder(WorldModel):
    kind: Literal["declare_war"] = "declare_war"
    faction_id: FactionId
    target_faction_id: FactionId
    ground_id: str | None = None


class CallNegotiationOrder(WorldModel):
    kind: Literal["call_negotiation"] = "call_negotiation"
    faction_id: FactionId
    target_faction_id: FactionId


class FabricateClaimOrder(WorldModel):
    kind: Literal["fabricate_claim"] = "fabricate_claim"
    faction_id: FactionId
    target_faction_id: FactionId
    region_id: RegionId


class ProposeAgreementOrder(WorldModel):
    kind: Literal["propose_agreement"] = "propose_agreement"
    faction_id: FactionId
    target_faction_id: FactionId
    agreement: Literal["alliance", "trade_deal", "truce"]


class SendEnvoyOrder(WorldModel):
    kind: Literal["send_envoy"] = "send_envoy"
    faction_id: FactionId
    target_faction_id: FactionId


class HandlePrisonerOrder(WorldModel):
    kind: Literal["handle_prisoner"] = "handle_prisoner"
    faction_id: FactionId
    prisoner_id: EntityId
    action: Literal["ransom", "exchange", "release", "execute"]


class MediateOrder(WorldModel):
    kind: Literal["mediate"] = "mediate"
    faction_id: FactionId
    war_id: str


class AnswerCallOrder(WorldModel):
    kind: Literal["answer_call"] = "answer_call"
    faction_id: FactionId
    call_id: str
    is_joining: bool


class DenounceAllianceOrder(WorldModel):
    kind: Literal["denounce_alliance"] = "denounce_alliance"
    faction_id: FactionId
    alliance_id: str


class DemandFromVassalOrder(WorldModel):
    kind: Literal["demand_from_vassal"] = "demand_from_vassal"
    faction_id: FactionId
    vassalage_id: str
    demand_kind: DemandKind
    amount: WholeNumber


class AnswerDemandOrder(WorldModel):
    kind: Literal["answer_demand"] = "answer_demand"
    faction_id: FactionId
    demand_id: str
    reply: DemandReply


class GrantConsentOrder(WorldModel):
    kind: Literal["grant_consent"] = "grant_consent"
    faction_id: FactionId
    vassalage_id: str
    action: ConsentAction
    target_faction_id: FactionId


class ReleaseVassalOrder(WorldModel):
    kind: Literal["release_vassal"] = "release_vassal"
    faction_id: FactionId
    vassalage_id: str


class AnnexVassalOrder(WorldModel):
    kind: Literal["annex_vassal"] = "annex_vassal"
    faction_id: FactionId
    vassalage_id: str


class AnswerEventOrder(WorldModel):
    kind: Literal["answer_event"] = "answer_event"
    faction_id: FactionId
    event_id: EntityId
    choice_id: EntityId


Order = Annotated[
    MapScoutOrder
    | MoveArmyOrder
    | HaltArmyOrder
    | AttackOrder
    | BesiegeOrder
    | RaiseArmyOrder
    | DisbandArmyOrder
    | MergeArmiesOrder
    | SplitArmyOrder
    | SetPayOrder
    | SetTaxRateOrder
    | TakeLoanOrder
    | DeclareDefaultOrder
    | BuildImprovementOrder
    | DiplomaticPlayOrder
    | DeclareWarOrder
    | CallNegotiationOrder
    | FabricateClaimOrder
    | ProposeAgreementOrder
    | SendEnvoyOrder
    | HandlePrisonerOrder
    | MediateOrder
    | AnswerCallOrder
    | DenounceAllianceOrder
    | DemandFromVassalOrder
    | AnswerDemandOrder
    | GrantConsentOrder
    | ReleaseVassalOrder
    | AnnexVassalOrder
    | AnswerEventOrder,
    Field(discriminator="kind"),
]


class QueuedOrder(WorldModel):
    id: str
    order: Order
    cost: WholeNumber
    queued_turn: WholeNumber
