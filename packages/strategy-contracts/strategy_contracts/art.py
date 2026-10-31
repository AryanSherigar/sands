from typing import Literal
from uuid import UUID

from pydantic import Field

from strategy_contracts.base import StrictModel

ART_PROMPT_VERSION = "strategy-art-v1"
MAX_ART_URL_CHARS = 2048
MAX_ART_CAUSES = 12
MAX_ART_HEADLINE_CHARS = 160
MAX_ART_ITEM_ID_CHARS = 100
ART_ITEM_ID_PATTERN = r"^[A-Za-z0-9_-]+$"
ArtKind = Literal["event", "uprising", "chronicle"]
ArtStatus = Literal["pending", "generating", "completed", "failed"]
ArtErrorCode = Literal["provider_timeout", "provider_unavailable", "stream_cancelled"]


class ArtBriefing(StrictModel):
    kind: ArtKind
    item_id: str = Field(max_length=MAX_ART_ITEM_ID_CHARS)
    headline: str = Field(max_length=MAX_ART_HEADLINE_CHARS)
    subject_name: str | None = Field(default=None, max_length=MAX_ART_HEADLINE_CHARS)
    region_ids: list[str] = Field(default_factory=list)
    cause_keys: list[str] = Field(default_factory=list, max_length=MAX_ART_CAUSES)


class ArtView(StrictModel):
    kind: ArtKind
    item_id: str
    status: ArtStatus
    art_url: str | None = None
    error_code: str | None = None
    is_retryable: bool = False


class ArtClaimInput(StrictModel):
    claim_id: UUID


class ArtClaim(StrictModel):
    art: ArtView
    briefing: ArtBriefing | None = None
    lease_token: UUID | None = None


class ArtCompleteInput(StrictModel):
    lease_token: UUID
    art_url: str = Field(min_length=1, max_length=MAX_ART_URL_CHARS)
    prompt_version: Literal["strategy-art-v1"] = ART_PROMPT_VERSION


class ArtFailInput(StrictModel):
    lease_token: UUID
    error_code: ArtErrorCode
