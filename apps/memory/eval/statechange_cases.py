"""File format of the state-change fixture set: one self-contained case per line."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from eval.errors import HarnessError

CASES_FILE = Path(__file__).parent / "statechange" / "cases.jsonl"
MAX_TURNS_PER_CASE = 5
CaseCategory = Literal["change", "additive", "negation", "rejected", "outside_context"]


class CaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseEntity(CaseModel):
    key: str
    name: str
    aliases: list[str] = Field(default_factory=list)


class PriorFact(CaseModel):
    key: str
    subject: str
    predicate: str
    object_literal: str


class RejectedChange(CaseModel):
    entity: str
    attribute: str
    value: str


class CaseTurn(CaseModel):
    action: str
    narration: str
    rejected: list[RejectedChange] = Field(default_factory=list)


class RequiredFact(CaseModel):
    subject: str | None = None
    words: list[str] = Field(min_length=1)


class ForbiddenFact(CaseModel):
    words: list[str] = Field(min_length=1)


class Expectation(CaseModel):
    superseded: list[str] = Field(default_factory=list)
    kept: list[str] = Field(default_factory=list)
    required: list[RequiredFact] = Field(default_factory=list)
    forbidden: list[ForbiddenFact] = Field(default_factory=list)


class StateChangeCase(CaseModel):
    case_id: str
    category: CaseCategory
    note: str
    entities: list[CaseEntity] = Field(min_length=1)
    prior_facts: list[PriorFact] = Field(default_factory=list)
    filler_subject: str | None = None
    filler_count: int = 0
    turns: list[CaseTurn] = Field(min_length=1, max_length=MAX_TURNS_PER_CASE)
    expect: Expectation

    @model_validator(mode="after")
    def _references_resolve(self) -> "StateChangeCase":
        entity_keys = {entity.key for entity in self.entities}
        fact_keys = {fact.key for fact in self.prior_facts}
        self._check_keys(
            {fact.subject for fact in self.prior_facts}, entity_keys, "subject"
        )
        self._check_keys(
            {*self.expect.superseded, *self.expect.kept}, fact_keys, "fact key"
        )
        subjects = {item.subject for item in self.expect.required if item.subject}
        self._check_keys(subjects, entity_keys, "required subject")
        rejected = {item.entity for turn in self.turns for item in turn.rejected}
        self._check_keys(rejected, entity_keys, "rejected entity")
        if self.filler_subject is not None:
            self._check_keys({self.filler_subject}, entity_keys, "filler subject")
        if set(self.expect.superseded) & set(self.expect.kept):
            raise ValueError("a fact cannot be both superseded and kept")
        return self

    def _check_keys(self, used: set[str], known: set[str], what: str) -> None:
        unknown = used - known
        if unknown:
            raise ValueError(f"{self.case_id}: unknown {what} {sorted(unknown)}")


def load_cases(path: Path = CASES_FILE) -> list[StateChangeCase]:
    lines = path.read_text(encoding="utf-8").splitlines()
    cases = [
        StateChangeCase.model_validate_json(line) for line in lines if line.strip()
    ]
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise HarnessError("state-change case ids must be unique")
    return cases
