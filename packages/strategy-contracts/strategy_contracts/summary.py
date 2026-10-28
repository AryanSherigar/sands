from typing import Literal
from uuid import UUID

from pydantic import Field

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import WholeNumber

MAX_SUMMARY_EVENTS = 100
MAX_SUMMARY_PACKAGE_CHARS = 32000
MAX_SUMMARY_PROSE_CHARS = 16000
SummaryTrigger = Literal["major_event", "significance"]
SummaryStatus = Literal["pending", "generating", "completed", "failed"]


class SummaryFact(StrictModel):
    event_id: UUID
    kind: str = Field(max_length=100)
    turn: WholeNumber
    text_key: str = Field(max_length=160)
    region_ids: list[str] = Field(default_factory=list)
    values: dict[str, int | str] = Field(default_factory=dict)


class SummaryBriefing(StrictModel):
    contract_version: Literal[1] = 1
    summary_id: UUID
    playthrough_id: UUID
    observer_faction_id: str
    requested_turn: WholeNumber
    trigger: SummaryTrigger
    facts: list[SummaryFact] = Field(min_length=1, max_length=MAX_SUMMARY_EVENTS)


class SummaryView(StrictModel):
    summary_id: UUID
    requested_turn: WholeNumber
    trigger: SummaryTrigger
    status: SummaryStatus
    narration: str | None = None
    error_code: str | None = None
    is_retryable: bool = False
    region_ids: list[str] = Field(default_factory=list)


class SummaryPage(StrictModel):
    items: list[SummaryView] = Field(default_factory=list)
    next_after_id: UUID | None = None


class SummaryClaimInput(StrictModel):
    claim_id: UUID


class SummaryCompleteInput(StrictModel):
    lease_token: UUID
    input_hash: str = Field(min_length=64, max_length=64)
    narration: str = Field(min_length=1, max_length=MAX_SUMMARY_PROSE_CHARS)
    prompt_version: Literal["chronicle-v1"] = "chronicle-v1"


class SummaryFailInput(StrictModel):
    lease_token: UUID
    error_code: Literal["provider_timeout", "provider_unavailable", "stream_cancelled"]


class SummaryClaim(StrictModel):
    summary: SummaryView
    briefing: SummaryBriefing
    input_hash: str
    lease_token: UUID | None = None


class SummaryAvailability(StrictModel):
    pending_count: WholeNumber = 0
    latest_summary_id: UUID | None = None
