from enum import StrEnum

from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import FactionId, Percent, RegionId, WholeNumber

DEFAULT_COVENANT_TURNS = 8
DEFAULT_COVENANT_UNREST_REDUCTION = 25
DEFAULT_RELIEF_SMALL_GOLD = 30
DEFAULT_RELIEF_LARGE_GOLD = 80
DEFAULT_BREACH_UNREST = 20
DEFAULT_BREACH_REPUTATION_COST = 10
DEFAULT_BREACH_LOCKOUT_TURNS = 6
DEFAULT_REVOLT_EXCHANGE_CAP = 4


class CovenantKind(StrEnum):
    TAX_RELIEF = "tax_relief"
    GARRISON_OUT = "garrison_out"
    RELIEF_SMALL = "relief_small"
    RELIEF_LARGE = "relief_large"
    AMNESTY = "amnesty"


class CovenantStatus(StrEnum):
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    BREACHED = "breached"
    EXPIRED = "expired"


class RelapseStage(StrEnum):
    RIOT = "riot"
    ARMED = "armed"


NO_TERMS_OPTION_ID = "no_terms"


class RevoltTalkOption(StrictModel):
    id: str
    label: str
    covenants: tuple[CovenantKind, ...]


REVOLT_TALK_OPTIONS = (
    RevoltTalkOption(
        id=NO_TERMS_OPTION_ID, label="Offer nothing but words", covenants=()
    ),
    RevoltTalkOption(
        id="tax_relief", label="Lower the taxes", covenants=(CovenantKind.TAX_RELIEF,)
    ),
    RevoltTalkOption(
        id="garrison_out",
        label="Keep soldiers out of the region",
        covenants=(CovenantKind.GARRISON_OUT,),
    ),
    RevoltTalkOption(
        id="relief_small",
        label="Open the granaries a little",
        covenants=(CovenantKind.RELIEF_SMALL,),
    ),
    RevoltTalkOption(
        id="relief_large",
        label="Pay a great relief",
        covenants=(CovenantKind.RELIEF_LARGE,),
    ),
    RevoltTalkOption(
        id="amnesty",
        label="Pardon the rebels",
        covenants=(CovenantKind.AMNESTY,),
    ),
    RevoltTalkOption(
        id="charter",
        label="Grant a charter: lower taxes and no soldiers",
        covenants=(CovenantKind.TAX_RELIEF, CovenantKind.GARRISON_OUT),
    ),
)
OPTION_BY_ID = {option.id: option for option in REVOLT_TALK_OPTIONS}
BREACHABLE_KINDS = frozenset(
    {CovenantKind.TAX_RELIEF, CovenantKind.GARRISON_OUT, CovenantKind.AMNESTY}
)


class CovenantState(StrictModel):
    id: str
    faction_id: FactionId
    region_id: RegionId
    covenant: CovenantKind
    start_turn: WholeNumber
    end_turn: WholeNumber
    relapse_stage: RelapseStage = RelapseStage.RIOT
    status: CovenantStatus = CovenantStatus.ACTIVE
    origin_scene_id: str | None = None


class RevoltTalkTuning(StrictModel):
    is_enabled: bool = False
    covenant_turns: int = Field(default=DEFAULT_COVENANT_TURNS, ge=1)
    covenant_unrest_reduction: Percent = DEFAULT_COVENANT_UNREST_REDUCTION
    relief_small_gold: int = Field(default=DEFAULT_RELIEF_SMALL_GOLD, ge=0)
    relief_large_gold: int = Field(default=DEFAULT_RELIEF_LARGE_GOLD, ge=0)
    breach_unrest: Percent = DEFAULT_BREACH_UNREST
    breach_reputation_cost: Percent = DEFAULT_BREACH_REPUTATION_COST
    breach_lockout_turns: int = Field(default=DEFAULT_BREACH_LOCKOUT_TURNS, ge=0)
