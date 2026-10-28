from enum import Enum
from typing import Annotated, Literal

from pydantic import Field

from strategy_contracts.alliance import AllianceType
from strategy_contracts.base import StrictModel
from strategy_contracts.ids import EntityId, FactionId, LeaderId, RegionId, WholeNumber
from strategy_contracts.limits import FULL_SHARE_PERCENT, MAX_TERMS_PER_CARD
from strategy_contracts.peace import PeaceTier


class TermKind(str, Enum):
    CEDE_REGION = "cede_region"
    PAY_GOLD = "pay_gold"
    TRIBUTE = "tribute"
    RELEASE_PRISONERS = "release_prisoners"
    NON_AGGRESSION = "non_aggression"
    ALLIANCE = "alliance"
    MILITARY_ACCESS = "military_access"
    TRADE_DEAL = "trade_deal"
    HOSTAGE = "hostage"
    PEACE = "peace"
    VASSAL = "vassal"


class CedeRegionTerm(StrictModel):
    kind: Literal["cede_region"] = "cede_region"
    from_faction_id: FactionId
    to_faction_id: FactionId
    region_id: RegionId


class PayGoldTerm(StrictModel):
    kind: Literal["pay_gold"] = "pay_gold"
    payer_id: FactionId
    payee_id: FactionId
    amount: WholeNumber


class TributeTerm(StrictModel):
    kind: Literal["tribute"] = "tribute"
    payer_id: FactionId
    payee_id: FactionId
    gold_per_turn: WholeNumber
    duration_turns: int = Field(ge=1)


class ReleasePrisonersTerm(StrictModel):
    kind: Literal["release_prisoners"] = "release_prisoners"
    holder_id: FactionId
    recipient_id: FactionId
    prisoner_ids: list[EntityId]
    ransom_gold: WholeNumber = 0


class NonAggressionTerm(StrictModel):
    kind: Literal["non_aggression"] = "non_aggression"
    faction_a: FactionId
    faction_b: FactionId
    duration_turns: int = Field(ge=1)


class AllianceTerm(StrictModel):
    kind: Literal["alliance"] = "alliance"
    faction_a: FactionId
    faction_b: FactionId
    alliance_type: AllianceType = AllianceType.DEFENSIVE
    duration_turns: WholeNumber = 0
    is_separate_peace_banned: bool = False


class MilitaryAccessTerm(StrictModel):
    kind: Literal["military_access"] = "military_access"
    grantor_id: FactionId
    grantee_id: FactionId
    duration_turns: int = Field(ge=1)


class TradeDealTerm(StrictModel):
    kind: Literal["trade_deal"] = "trade_deal"
    faction_a: FactionId
    faction_b: FactionId
    duration_turns: int = Field(ge=1)


class HostageTerm(StrictModel):
    kind: Literal["hostage"] = "hostage"
    giver_id: FactionId
    holder_id: FactionId
    leader_id: LeaderId
    duration_turns: int = Field(ge=1)


class PeaceTerm(StrictModel):
    kind: Literal["peace"] = "peace"
    faction_a: FactionId
    faction_b: FactionId
    tier: PeaceTier
    guarantor_ids: list[FactionId] = Field(default_factory=list)
    is_white_peace: bool = False
    party_ids: list[FactionId] = Field(default_factory=list)


class VassalTerm(StrictModel):
    kind: Literal["vassal"] = "vassal"
    overlord_id: FactionId
    vassal_id: FactionId
    tribute_share_percent: int = Field(ge=0, le=FULL_SHARE_PERCENT)
    levy_share_percent: int = Field(default=0, ge=0, le=FULL_SHARE_PERCENT)
    is_foreign_policy_controlled: bool = False
    has_garrison_rights: bool = False
    duration_turns: WholeNumber = 0


Term = Annotated[
    CedeRegionTerm
    | PayGoldTerm
    | TributeTerm
    | ReleasePrisonersTerm
    | NonAggressionTerm
    | AllianceTerm
    | MilitaryAccessTerm
    | TradeDealTerm
    | HostageTerm
    | PeaceTerm
    | VassalTerm,
    Field(discriminator="kind"),
]


class TermsCard(StrictModel):
    proposer_id: FactionId
    counterpart_id: FactionId
    terms: list[Term] = Field(min_length=1, max_length=MAX_TERMS_PER_CARD)
    is_confirmed_by_player: bool = False
    is_confirmed_by_counterpart: bool = False
