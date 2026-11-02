from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from strategy_contracts.alliance import AllianceType
from strategy_contracts.base import StrictModel
from strategy_contracts.condition_templates import ConditionClause
from strategy_contracts.ids import EntityId, FactionId, LeaderId, RegionId, WholeNumber
from strategy_contracts.limits import (
    FULL_SHARE_PERCENT,
    MAX_CONDITIONAL_EXPIRY_TURNS,
    MAX_TERMS_PER_CARD,
)
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
    SWORN_PROMISE = "sworn_promise"
    CONDITIONAL = "conditional"


class PromiseKind(str, Enum):
    NEVER_ATTACK_FACTION = "never_attack_faction"
    NEVER_ALLY_WITH = "never_ally_with"
    SPARE_PRISONERS = "spare_prisoners"
    NEVER_OCCUPY_REGION = "never_occupy_region"


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


SUBJECT_PROMISE_KINDS = frozenset(
    {PromiseKind.NEVER_ALLY_WITH, PromiseKind.NEVER_OCCUPY_REGION}
)


class SwornPromiseTerm(StrictModel):
    kind: Literal["sworn_promise"] = "sworn_promise"
    promisor_id: FactionId
    beneficiary_id: FactionId
    promise: PromiseKind
    subject_id: EntityId | None = None
    duration_turns: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_parties_and_subject(self) -> "SwornPromiseTerm":
        if self.promisor_id == self.beneficiary_id:
            raise ValueError("a promise needs two different parties")
        needs_subject = self.promise in SUBJECT_PROMISE_KINDS
        if needs_subject and self.subject_id is None:
            raise ValueError(f"{self.promise.value} needs a subject")
        if not needs_subject and self.subject_id is not None:
            raise ValueError(f"{self.promise.value} takes no subject")
        if self.subject_id in (self.promisor_id, self.beneficiary_id):
            raise ValueError("the subject must be a third party")
        return self


BaseTerm = Annotated[
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
    | VassalTerm
    | SwornPromiseTerm,
    Field(discriminator="kind"),
]


class ConditionalMode(str, Enum):
    TRIGGER = "trigger"
    GATE = "gate"


PARTY_FIELDS = (
    "faction_a",
    "faction_b",
    "from_faction_id",
    "to_faction_id",
    "payer_id",
    "payee_id",
    "holder_id",
    "recipient_id",
    "grantor_id",
    "grantee_id",
    "giver_id",
    "promisor_id",
    "beneficiary_id",
    "overlord_id",
    "vassal_id",
)
CONDITIONABLE_KINDS = frozenset(
    {
        TermKind.CEDE_REGION,
        TermKind.PAY_GOLD,
        TermKind.TRIBUTE,
        TermKind.NON_AGGRESSION,
        TermKind.ALLIANCE,
        TermKind.MILITARY_ACCESS,
        TermKind.TRADE_DEAL,
        TermKind.VASSAL,
        TermKind.SWORN_PROMISE,
    }
)
GATEABLE_KINDS = frozenset(
    {
        TermKind.TRIBUTE,
        TermKind.NON_AGGRESSION,
        TermKind.MILITARY_ACCESS,
        TermKind.TRADE_DEAL,
        TermKind.SWORN_PROMISE,
    }
)


def term_party_ids(term: BaseTerm) -> frozenset[str]:
    return frozenset(
        getattr(term, field) for field in PARTY_FIELDS if hasattr(term, field)
    )


class ConditionalTerm(StrictModel):
    kind: Literal["conditional"] = "conditional"
    mode: ConditionalMode
    when: ConditionClause
    expires_in_turns: int = Field(ge=1, le=MAX_CONDITIONAL_EXPIRY_TURNS)
    inner: BaseTerm

    @model_validator(mode="after")
    def validate_inner_and_condition(self) -> "ConditionalTerm":
        kind = TermKind(self.inner.kind)
        allowed = (
            GATEABLE_KINDS if self.mode is ConditionalMode.GATE else CONDITIONABLE_KINDS
        )
        if kind not in allowed:
            raise ValueError(f"a {self.mode.value} cannot wrap a {kind.value} clause")
        if self.when.faction_id not in term_party_ids(self.inner):
            raise ValueError("the condition must watch a party of the clause")
        return self


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
    | VassalTerm
    | SwornPromiseTerm
    | ConditionalTerm,
    Field(discriminator="kind"),
]


class TermsCard(StrictModel):
    proposer_id: FactionId
    counterpart_id: FactionId
    terms: list[Term] = Field(min_length=1, max_length=MAX_TERMS_PER_CARD)
    is_confirmed_by_player: bool = False
    is_confirmed_by_counterpart: bool = False
