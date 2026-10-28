"""Row shapes of the alpha data export.

Testers are identified by `user_id` alone; none of these models carries a
display name, Firebase UID, email or invite label.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ToolCallSummary(BaseModel):
    tool_name: str
    is_valid: bool


class TurnMetricsExport(BaseModel):
    first_token_ms: int | None
    generation_ms: int | None
    total_ms: int
    step_durations: dict[str, int]
    memory_degraded_reasons: list[str]
    memory_retrieval_ms: int | None
    memory_facts_returned: int | None
    fired_condition_ids: list[str]
    dropped_mutation_count: int
    dropped_mutation_paths: list[str]
    check_outcomes: list[dict[str, object]]
    stat_snapshot: dict[str, float]
    replay_count: int


class TranscriptTurnExport(BaseModel):
    user_id: uuid.UUID
    playthrough_id: uuid.UUID
    playthrough_status: str
    ended_outcome_tag: str | None
    ended_outcome_title: str | None
    turn_number: int
    action_text: str
    action_mode: str
    narration_text: str | None
    tool_calls: list[ToolCallSummary]
    location_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    model_name: str | None
    created_at: datetime
    metrics: TurnMetricsExport | None


class MetricsRowExport(TurnMetricsExport):
    user_id: uuid.UUID
    playthrough_id: uuid.UUID
    turn_number: int
    created_at: datetime


class EventExport(BaseModel):
    user_id: uuid.UUID
    playthrough_id: uuid.UUID | None
    session_id: str
    name: str
    props: dict[str, object]
    source: str
    client_ts: datetime | None
    received_at: datetime


class FeedbackExport(BaseModel):
    user_id: uuid.UUID
    playthrough_id: uuid.UUID
    turn_number: int | None
    category: str
    body: str
    created_at: datetime


class NarrationFlagExport(BaseModel):
    user_id: uuid.UUID
    playthrough_id: uuid.UUID
    turn_id: uuid.UUID
    reasons: list[str]
    note: str | None
    created_at: datetime


class SurveyExport(BaseModel):
    user_id: uuid.UUID
    playthrough_id: uuid.UUID | None
    kind: str
    answers: dict[str, object]
    created_at: datetime
