from enum import Enum

from pydantic import Field, field_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import AmbitionId, LeaderId, TraitId
from strategy_contracts.limits import MAX_NAME_CHARS, MAX_TEXT_CHARS

DEFAULT_AILING_AGE = 55
DEFAULT_FAILING_AGE = 70
DEFAULT_STRESS_WORSENS_AT = 70
DEFAULT_OLD_AGE_STEP_PER_MILLE = 5
DEFAULT_MAX_DEATH_PER_MILLE = 500
DEFAULT_CRISIS_TURNS = 6
DEFAULT_CRISIS_STABILITY_LOSS = 3
DEFAULT_CRISIS_UNREST = 2
DEFAULT_CRISIS_ACCEPTANCE_SHIFT = 5
DEFAULT_COMING_OF_AGE = 16
DEFAULT_REGENT_AGE = 45
DEFAULT_OPINION_CARRY_PERCENT = 50
DEFAULT_REGENT_TRAIT_IDS = ("pragmatic", "cautious")
MAX_HEIR_DEPTH = 2
MIN_REGENT_TRAITS = 2
MAX_REGENT_TRAITS = 3
MAX_PLAUSIBLE_HEIR_AGE = 80
MAX_PLAUSIBLE_RULER_AGE = 100
PER_MILLE = 1000


class HealthBand(str, Enum):
    ROBUST = "robust"
    AILING = "ailing"
    FAILING = "failing"


DEFAULT_DEATH_PER_MILLE: dict[HealthBand, int] = {
    HealthBand.ROBUST: 2,
    HealthBand.AILING: 25,
    HealthBand.FAILING: 120,
}


class HeirSetup(StrictModel):
    id: LeaderId
    name: str = Field(min_length=1, max_length=MAX_NAME_CHARS)
    trait_ids: list[TraitId] = Field(default_factory=list)
    ambition_ids: list[AmbitionId] = Field(default_factory=list)
    age: int = Field(default=0, ge=0)
    history: str = Field(default="", max_length=MAX_TEXT_CHARS)
    heir: "HeirSetup | None" = None


def heir_chain(heir: HeirSetup | None) -> list[HeirSetup]:
    chain: list[HeirSetup] = []
    while heir is not None:
        chain.append(heir)
        heir = heir.heir
    return chain


def heir_depth(heir: HeirSetup | None) -> int:
    return len(heir_chain(heir))


def _default_death_per_mille() -> dict[HealthBand, int]:
    return dict(DEFAULT_DEATH_PER_MILLE)


def _default_regent_trait_ids() -> list[TraitId]:
    return list(DEFAULT_REGENT_TRAIT_IDS)


class SuccessionTuning(StrictModel):
    rule_version: str = "succession-v1"
    ailing_age: int = Field(default=DEFAULT_AILING_AGE, ge=0)
    failing_age: int = Field(default=DEFAULT_FAILING_AGE, ge=0)
    stress_worsens_at: int = Field(default=DEFAULT_STRESS_WORSENS_AT, ge=0, le=100)
    death_per_mille: dict[HealthBand, int] = Field(
        default_factory=_default_death_per_mille
    )
    old_age_step_per_mille: int = Field(default=DEFAULT_OLD_AGE_STEP_PER_MILLE, ge=0)
    max_death_per_mille: int = Field(
        default=DEFAULT_MAX_DEATH_PER_MILLE, ge=0, le=PER_MILLE
    )
    crisis_turns: int = Field(default=DEFAULT_CRISIS_TURNS, ge=1)
    crisis_stability_loss: int = Field(default=DEFAULT_CRISIS_STABILITY_LOSS, ge=0)
    crisis_unrest: int = Field(default=DEFAULT_CRISIS_UNREST, ge=0)
    crisis_acceptance_shift: int = Field(default=DEFAULT_CRISIS_ACCEPTANCE_SHIFT, ge=0)
    coming_of_age: int = Field(default=DEFAULT_COMING_OF_AGE, ge=0)
    regent_age: int = Field(default=DEFAULT_REGENT_AGE, ge=0)
    opinion_carry_percent: int = Field(
        default=DEFAULT_OPINION_CARRY_PERCENT, ge=0, le=100
    )
    regent_trait_ids: list[TraitId] = Field(
        default_factory=_default_regent_trait_ids,
        min_length=MIN_REGENT_TRAITS,
        max_length=MAX_REGENT_TRAITS,
    )

    @field_validator("death_per_mille")
    @classmethod
    def validate_death_table(
        cls, table: dict[HealthBand, int]
    ) -> dict[HealthBand, int]:
        if set(table) != set(HealthBand):
            raise ValueError("death_per_mille must define every health band")
        if any(not 0 <= value <= PER_MILLE for value in table.values()):
            raise ValueError("death_per_mille values must be within 0 to 1000")
        return table
