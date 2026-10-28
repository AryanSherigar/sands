from app.models.base import WorldModel
from pydantic import Field
from strategy_contracts.ids import AmbitionId, Percent, RegionId, TraitId, WholeNumber
from strategy_contracts.limits import MAX_NAME_CHARS, MAX_TEXT_CHARS

MIN_RULER_TRAITS = 2
MAX_RULER_TRAITS = 3
MIN_RULER_AMBITIONS = 1
MAX_RULER_AMBITIONS = 2


class PlayerProfile(WorldModel):
    tactic_use_counts: dict[str, WholeNumber] = Field(default_factory=dict)
    formation_use_counts: dict[str, WholeNumber] = Field(default_factory=dict)
    wars_declared: WholeNumber = 0
    peace_deals: WholeNumber = 0
    promises_kept: WholeNumber = 0
    promises_broken: WholeNumber = 0
    mercy_acts: WholeNumber = 0
    cruelty_acts: WholeNumber = 0
    honest_statements: WholeNumber = 0
    deceit_statements: WholeNumber = 0
    tone_grade_total: WholeNumber = 0
    tone_grade_count: WholeNumber = 0
    pushed_region_counts: dict[RegionId, WholeNumber] = Field(default_factory=dict)


class PlayerRuler(WorldModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_CHARS)
    epithet: str | None = Field(default=None, max_length=MAX_NAME_CHARS)
    portrait_url: str | None = None
    trait_ids: list[TraitId] = Field(
        min_length=MIN_RULER_TRAITS, max_length=MAX_RULER_TRAITS
    )
    ambition_ids: list[AmbitionId] = Field(
        min_length=MIN_RULER_AMBITIONS, max_length=MAX_RULER_AMBITIONS
    )
    backstory: str = Field(default="", max_length=MAX_TEXT_CHARS)
    stress: Percent = 0
