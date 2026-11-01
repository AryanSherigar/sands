"""Turn metrics record: the shape a turn's collector hands to the repository."""

from pydantic import BaseModel, Field

CHECK_RESULT_PASSED = "passed"
CHECK_RESULT_FAILED = "failed"
CHECK_RESULT_TIMEOUT = "timeout"
CHECK_RESULT_HIDDEN = "hidden"


class CheckOutcome(BaseModel):
    check_id: str
    kind: str
    result: str
    answer_ms: int | None = None
    composure_score: int | None = None


class TurnMetricsRecord(BaseModel):
    first_token_ms: int | None = None
    generation_ms: int | None = None
    total_ms: int
    step_durations: dict[str, int] = Field(default_factory=dict)
    memory_degraded_reasons: list[str] = Field(default_factory=list)
    memory_retrieval_ms: int | None = None
    memory_facts_returned: int | None = None
    fired_condition_ids: list[str] = Field(default_factory=list)
    dropped_mutation_count: int = 0
    dropped_mutation_paths: list[str] = Field(default_factory=list)
    check_outcomes: list[CheckOutcome] = Field(default_factory=list)
    stat_snapshot: dict[str, float] = Field(default_factory=dict)
