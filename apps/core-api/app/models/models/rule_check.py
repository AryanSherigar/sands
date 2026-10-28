"""Pydantic request and response schemas for rule checks (tool `rule_checks`).

StateMutation is imported from app.models.condition, never redefined.
"""

import uuid

from app.models.condition import StateMutation
from pydantic import BaseModel, ConfigDict, Field, model_validator

RULE_CHECK_KINDS = ("timed_choice", "recall", "time_entry")
_RULE_CHECK_KIND_PATTERN = "^(" + "|".join(RULE_CHECK_KINDS) + ")$"
MAX_OPTION_MUTATIONS = 8
MAX_VARIANT_LENGTH = 200
MINUTES_PER_DAY = 1440
DEFAULT_ENTER_LABEL = "Write it in the Log"
DEFAULT_REJECT_LABEL = "Reject the visitor"


class CheckOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,30}$")
    label: str = Field(max_length=120)
    result: str
    mutations: list[StateMutation] = Field(
        default_factory=list, max_length=MAX_OPTION_MUTATIONS
    )
    reopens: bool = False


class TimedChoiceParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(max_length=500)
    options: list[CheckOption] = Field(min_length=2, max_length=6)
    window_ms: int = Field(ge=1000, le=120_000)
    timeout_result: str
    hidden_result: str | None = None
    max_reopens: int = Field(default=3, ge=0, le=10)

    @model_validator(mode="after")
    def _validate_option_ids_are_unique(self) -> "TimedChoiceParams":
        option_ids = [option.id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("option ids must be unique")
        return self

    def result_values(self) -> list[str]:
        results = [option.result for option in self.options] + [self.timeout_result]
        return results + ([self.hidden_result] if self.hidden_result else [])

    def mutation_paths(self) -> list[str]:
        return [m.path for option in self.options for m in option.mutations]


class TimeEntryOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: str
    mutations: list[StateMutation] = Field(
        default_factory=list, max_length=MAX_OPTION_MUTATIONS
    )


class TimeEntryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(max_length=500)
    told_minute_of_day: int = Field(ge=0, lt=MINUTES_PER_DAY)
    clock_path: str = Field(max_length=255)
    clock_start_minute_of_day: int = Field(ge=0, lt=MINUTES_PER_DAY)
    window_ms: int = Field(ge=1000, le=120_000)
    timeout_result: str
    enter_label: str = Field(default=DEFAULT_ENTER_LABEL, max_length=120)
    reject_label: str = Field(default=DEFAULT_REJECT_LABEL, max_length=120)
    told: TimeEntryOutcome
    wall: TimeEntryOutcome
    other: TimeEntryOutcome
    reject: TimeEntryOutcome

    def _outcomes(self) -> list[TimeEntryOutcome]:
        return [self.told, self.wall, self.other, self.reject]

    def result_values(self) -> list[str]:
        return [outcome.result for outcome in self._outcomes()] + [self.timeout_result]

    def mutation_paths(self) -> list[str]:
        return [m.path for outcome in self._outcomes() for m in outcome.mutations]


class RecallParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(max_length=500)
    variants: list[str] = Field(min_length=2, max_length=5)
    correct_index: int = Field(ge=0)
    window_ms: int = Field(default=30_000, ge=5_000, le=120_000)
    result_correct: str
    result_wrong: str
    result_timeout: str

    @model_validator(mode="after")
    def _validate_variants(self) -> "RecallParams":
        if self.correct_index >= len(self.variants):
            raise ValueError("correct_index must point at one of the variants")
        for variant in self.variants:
            if not variant.strip() or len(variant) > MAX_VARIANT_LENGTH:
                raise ValueError(
                    f"each variant must be 1-{MAX_VARIANT_LENGTH} characters"
                )
        if len(set(self.variants)) != len(self.variants):
            raise ValueError("variants must be distinct")
        return self

    def result_values(self) -> list[str]:
        return [self.result_correct, self.result_wrong, self.result_timeout]

    def mutation_paths(self) -> list[str]:
        return []


PARAMS_MODELS: dict[str, type[TimedChoiceParams | RecallParams | TimeEntryParams]] = {
    "timed_choice": TimedChoiceParams,
    "recall": RecallParams,
    "time_entry": TimeEntryParams,
}


def normalise_params(kind: str, params: dict[str, object]) -> dict[str, object]:
    """Validate `params` against the kind's model and return its JSON dump."""
    return PARAMS_MODELS[kind].model_validate(params).model_dump(mode="json")


class RuleCheckCreate(BaseModel):
    """Payload to create a rule check on a master-mode scenario."""

    label: str = Field(..., max_length=255)
    kind: str = Field(..., pattern=_RULE_CHECK_KIND_PATTERN)
    trigger_condition_expression: dict[str, object] = Field(default_factory=dict)
    priority: int = 0
    result_path: str = Field(..., max_length=255)
    params: dict[str, object]
    narrator_instruction_template: str | None = None

    @model_validator(mode="after")
    def _normalise_params_for_kind(self) -> "RuleCheckCreate":
        self.params = normalise_params(self.kind, self.params)
        return self


class RuleCheckUpdate(BaseModel):
    """Partial update; the service re-validates the merged result."""

    label: str | None = Field(default=None, max_length=255)
    kind: str | None = Field(default=None, pattern=_RULE_CHECK_KIND_PATTERN)
    trigger_condition_expression: dict[str, object] | None = None
    priority: int | None = None
    result_path: str | None = Field(default=None, max_length=255)
    params: dict[str, object] | None = None
    narrator_instruction_template: str | None = None


class RuleCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    check_id: uuid.UUID
    scenario_id: uuid.UUID
    label: str
    kind: str
    trigger_condition_expression: dict[str, object] = Field(default_factory=dict)
    priority: int = 0
    result_path: str
    params: dict[str, object] = Field(default_factory=dict)
    narrator_instruction_template: str | None = None


class RuleCheckListResponse(BaseModel):
    items: list[RuleCheckResponse]


class RuleCheckReorderRequest(BaseModel):
    ordered_check_ids: list[uuid.UUID]
