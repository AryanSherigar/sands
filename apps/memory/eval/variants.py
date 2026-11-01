"""Pre-registered tuning rounds and the log of every variant ever tried."""

import json
import re
from pathlib import Path
from typing import Literal

from app.config import Settings
from pydantic import BaseModel, Field, field_validator, model_validator

from eval.errors import HarnessError, VariantCapError

MAX_TOTAL_VARIANTS = 24
MAX_VARIANTS_PER_ROUND = 4
DEFAULT_REPEATS = 5
VARIANT_LOG_FILE = Path(__file__).parent / "reports" / "variant_log.jsonl"
MAX_SLUG_LENGTH = 20
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
FORBIDDEN_ENV = frozenset(
    {"memory_database_url", "embedding_api_key", "extraction_api_key"}
)
REGISTERED = "registered"
RESULT = "result"

Family = Literal[
    "extraction_prompt_validator",
    "extraction_model_shape",
    "retrieval_levers",
    "budget_window_embedding",
]


def check_slug(value: str) -> str:
    if not SLUG_PATTERN.match(value) or len(value) > MAX_SLUG_LENGTH:
        raise ValueError(
            f"{value!r} is not a lowercase slug of at most {MAX_SLUG_LENGTH} characters"
        )
    return value


class Variant(BaseModel):
    variant_id: str
    description: str
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("variant_id")
    @classmethod
    def _is_slug(cls, value: str) -> str:
        return check_slug(value)

    @field_validator("env")
    @classmethod
    def _knows_every_setting(cls, env: dict[str, str]) -> dict[str, str]:
        for name in env:
            key = name.lower()
            if key in FORBIDDEN_ENV or key not in Settings.model_fields:
                raise ValueError(f"{name} is not a tunable service setting")
        return env


class VariantRound(BaseModel):
    round_id: str
    family: Family
    base_run_ids: list[str] = Field(default_factory=list)
    base: Variant
    variants: list[Variant] = Field(min_length=1, max_length=MAX_VARIANTS_PER_ROUND)
    repeats: int = Field(default=DEFAULT_REPEATS, ge=1)

    @field_validator("round_id")
    @classmethod
    def _round_id_is_short(cls, value: str) -> str:
        return check_slug(value)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "VariantRound":
        ids = [self.base.variant_id, *(v.variant_id for v in self.variants)]
        if len(ids) != len(set(ids)):
            raise ValueError("variant ids in a round must be unique")
        return self

    def effective_env(self, variant: Variant) -> dict[str, str]:
        return {**self.base.env, **variant.env}


def load_round(path: Path) -> VariantRound:
    return VariantRound.model_validate_json(path.read_text(encoding="utf-8"))


def _entries(log_path: Path) -> list[dict[str, object]]:
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _append(log_path: Path, entries: list[dict[str, object]]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")


def registered_count(log_path: Path = VARIANT_LOG_FILE) -> int:
    return sum(1 for entry in _entries(log_path) if entry["kind"] == REGISTERED)


def register_round(round_: VariantRound, log_path: Path = VARIANT_LOG_FILE) -> None:
    entries = _entries(log_path)
    if any(entry["round_id"] == round_.round_id for entry in entries):
        raise HarnessError(f"Round {round_.round_id} is already registered")
    total = registered_count(log_path) + len(round_.variants)
    if total > MAX_TOTAL_VARIANTS:
        raise VariantCapError(
            f"Round {round_.round_id} would bring tried variants to {total}; "
            f"the pre-registered cap is {MAX_TOTAL_VARIANTS}"
        )
    _append(
        log_path,
        [
            {
                "kind": REGISTERED,
                "round_id": round_.round_id,
                "family": round_.family,
                "variant_id": variant.variant_id,
                "description": variant.description,
                "env": round_.effective_env(variant),
                "repeats": round_.repeats,
            }
            for variant in round_.variants
        ],
    )


def record_result(
    round_id: str,
    variant_id: str,
    run_ids: list[str],
    verdict: dict[str, object],
    log_path: Path = VARIANT_LOG_FILE,
) -> None:
    _append(
        log_path,
        [
            {
                "kind": RESULT,
                "round_id": round_id,
                "variant_id": variant_id,
                "run_ids": run_ids,
                "verdict": verdict,
            }
        ],
    )
