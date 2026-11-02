from typing import Annotated, Final, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from strategy_contracts.base import StrictModel
from strategy_contracts.chronicler import DEFAULT_CHRONICLER_ID, ChroniclerId
from strategy_contracts.ids import WholeNumber
from strategy_contracts.summary import SummaryFact, SummaryStatus

MAX_EPILOGUE_FACTS: Final[int] = 40
MAX_EPILOGUE_ENTRIES: Final[int] = 12
MAX_EPILOGUE_ENTRY_CHARS: Final[int] = 1500
MAX_EPILOGUE_PROSE_CHARS: Final[int] = 4000
MAX_EPILOGUE_HINT_CHARS: Final[int] = 600

EpilogueEntry = Annotated[str, StringConstraints(max_length=MAX_EPILOGUE_ENTRY_CHARS)]


class EpilogueBriefing(StrictModel):
    contract_version: Literal[1] = 1
    playthrough_id: UUID
    chronicler_id: ChroniclerId = DEFAULT_CHRONICLER_ID
    ruler_name: str
    ruler_trait_ids: list[str] = Field(default_factory=list)
    ending_id: str
    ending_kind: str
    ending_name: str = ""
    ending_hint: str = Field(default="", max_length=MAX_EPILOGUE_HINT_CHARS)
    grade: str | None = None
    ending_turn: WholeNumber
    headline_facts: list[SummaryFact] = Field(
        default_factory=list, max_length=MAX_EPILOGUE_FACTS
    )
    chronicle_entries: list[EpilogueEntry] = Field(
        default_factory=list, max_length=MAX_EPILOGUE_ENTRIES
    )


class EpilogueView(StrictModel):
    status: SummaryStatus
    narration: str | None = None
    error_code: str | None = None
    is_retryable: bool = False


class EpilogueClaimInput(StrictModel):
    claim_id: UUID


class EpilogueClaim(StrictModel):
    epilogue: EpilogueView
    briefing: EpilogueBriefing
    input_hash: str
    lease_token: UUID | None = None


class EpilogueCompleteInput(StrictModel):
    lease_token: UUID
    input_hash: str = Field(min_length=64, max_length=64)
    narration: str = Field(min_length=1, max_length=MAX_EPILOGUE_PROSE_CHARS)
    prompt_version: Literal["epilogue-v1"] = "epilogue-v1"


class EpilogueFailInput(StrictModel):
    lease_token: UUID
    error_code: Literal["provider_timeout", "provider_unavailable", "stream_cancelled"]
