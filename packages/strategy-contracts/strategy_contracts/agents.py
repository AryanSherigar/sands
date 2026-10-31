from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import WholeNumber
from strategy_contracts.pressure import PressureBand, RumorTopic

MAX_DISPATCH_PROSE_CHARS = 3000
MAX_AGENT_NAME_CHARS = 60
MAX_RUMOR_ID_CHARS = 100
RUMOR_ID_PATTERN = r"^[A-Za-z0-9_-]+$"
DispatchStatus = Literal["pending", "generating", "completed", "failed"]
DispatchErrorCode = Literal[
    "provider_timeout", "provider_unavailable", "stream_cancelled"
]


class AgentTrait(StrEnum):
    HONEST = "honest"
    DECEITFUL = "deceitful"
    PIOUS = "pious"
    INCOMPETENT = "incompetent"


class AgentTuning(StrictModel):
    is_enabled: bool = False
    loyalty_min: WholeNumber = 20
    loyalty_max: WholeNumber = 80
    pious_loyalty_bonus: WholeNumber = 15
    honest_wrong_reduction_percent: WholeNumber = 15
    incompetent_wrong_bonus_percent: WholeNumber = 20
    deceitful_calm_steps: WholeNumber = 1
    bribed_calm_steps: WholeNumber = 2
    bribe_base_price: WholeNumber = 40
    bribe_price_per_loyalty: WholeNumber = 2
    incompetent_bribe_discount_percent: WholeNumber = Field(default=30, le=100)
    bribe_score_bonus: WholeNumber = 6


class AgentView(StrictModel):
    name: str = Field(min_length=1, max_length=MAX_AGENT_NAME_CHARS)
    traits: list[AgentTrait]


class DispatchBriefing(StrictModel):
    contract_version: Literal[1] = 1
    rumor_id: str = Field(max_length=MAX_RUMOR_ID_CHARS)
    playthrough_id: UUID
    turn: WholeNumber
    agent: AgentView
    about_faction_id: str
    topic: RumorTopic
    reported_band: PressureBand


class DispatchView(StrictModel):
    rumor_id: str
    turn: WholeNumber
    agent: AgentView
    about_faction_id: str
    topic: RumorTopic
    status: DispatchStatus
    narration: str | None = None
    fallback_line_key: str
    error_code: DispatchErrorCode | None = None


class DispatchClaimInput(StrictModel):
    claim_id: UUID


class DispatchClaim(StrictModel):
    dispatch: DispatchView
    briefing: DispatchBriefing | None = None
    lease_token: UUID | None = None


class DispatchCompleteInput(StrictModel):
    lease_token: UUID
    narration: str = Field(min_length=1, max_length=MAX_DISPATCH_PROSE_CHARS)


class DispatchFailInput(StrictModel):
    lease_token: UUID
    error_code: DispatchErrorCode
