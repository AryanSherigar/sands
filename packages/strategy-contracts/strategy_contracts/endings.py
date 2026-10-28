from enum import Enum

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import WholeNumber
from strategy_contracts.limits import FULL_SHARE_PERCENT

DEFAULT_REGIME_FALL_WAR_SCORE_DEFICIT = 20
DEFAULT_REGIME_FALL_WILL_CEILING = 25
DEFAULT_REGIME_FALL_STABILITY_CEILING = 30
DEFAULT_REGIME_FALL_STREAK_TURNS = 4
DEFAULT_HEGEMONY_REGION_PERCENT = 60
DEFAULT_HEGEMONY_WEALTH_PERCENT = 60
DEFAULT_HEGEMONY_STREAK_TURNS = 6
DEFAULT_NEGOTIATED_MIN_TRUCE_TURNS = 8
DEFAULT_WEIGHT_POSITION = 30
DEFAULT_WEIGHT_STABILITY = 20
DEFAULT_WEIGHT_TREASURY = 15
DEFAULT_WEIGHT_WILL = 15
DEFAULT_WEIGHT_STRAIN = 20
DEFAULT_TREASURY_SCALE = 1000
DEFAULT_GRADE_THRESHOLDS = (30, 55, 80)
DEFAULT_PYRRHIC_POSITION_FLOOR = 50
DEFAULT_PYRRHIC_STRAIN_FLOOR = 60
GRADE_THRESHOLD_COUNT = 3


class EndingGrade(str, Enum):
    TRIUMPH = "triumph"
    HONORABLE = "honorable"
    PYRRHIC = "pyrrhic"
    BITTER = "bitter"
    RUIN = "ruin"


GRADE_ORDER = (
    EndingGrade.TRIUMPH,
    EndingGrade.HONORABLE,
    EndingGrade.PYRRHIC,
    EndingGrade.BITTER,
    EndingGrade.RUIN,
)


class EndingToggles(StrictModel):
    is_regime_fall_enabled: bool = True
    is_hegemony_enabled: bool = True
    is_negotiated_end_enabled: bool = True
    is_end_date_enabled: bool = True
    is_vassal_outcome_enabled: bool = True


class EndingsTuning(StrictModel):
    rule_version: int = Field(default=1, ge=1)
    toggles: EndingToggles = Field(default_factory=EndingToggles)
    regime_fall_war_score_deficit: WholeNumber = DEFAULT_REGIME_FALL_WAR_SCORE_DEFICIT
    regime_fall_will_ceiling: WholeNumber = DEFAULT_REGIME_FALL_WILL_CEILING
    regime_fall_stability_ceiling: WholeNumber = DEFAULT_REGIME_FALL_STABILITY_CEILING
    regime_fall_streak_turns: int = Field(
        default=DEFAULT_REGIME_FALL_STREAK_TURNS, ge=1
    )
    hegemony_region_percent: int = Field(
        default=DEFAULT_HEGEMONY_REGION_PERCENT, ge=1, le=FULL_SHARE_PERCENT
    )
    hegemony_wealth_percent: int = Field(
        default=DEFAULT_HEGEMONY_WEALTH_PERCENT, ge=1, le=FULL_SHARE_PERCENT
    )
    hegemony_streak_turns: int = Field(default=DEFAULT_HEGEMONY_STREAK_TURNS, ge=1)
    negotiated_min_truce_turns: int = Field(
        default=DEFAULT_NEGOTIATED_MIN_TRUCE_TURNS, ge=1
    )
    weight_position: WholeNumber = DEFAULT_WEIGHT_POSITION
    weight_stability: WholeNumber = DEFAULT_WEIGHT_STABILITY
    weight_treasury: WholeNumber = DEFAULT_WEIGHT_TREASURY
    weight_will: WholeNumber = DEFAULT_WEIGHT_WILL
    weight_strain: WholeNumber = DEFAULT_WEIGHT_STRAIN
    treasury_scale: int = Field(default=DEFAULT_TREASURY_SCALE, ge=1)
    grade_thresholds: list[int] = Field(
        default_factory=lambda: list(DEFAULT_GRADE_THRESHOLDS)
    )
    pyrrhic_position_floor: WholeNumber = DEFAULT_PYRRHIC_POSITION_FLOOR
    pyrrhic_strain_floor: WholeNumber = DEFAULT_PYRRHIC_STRAIN_FLOOR
    vassal_best_grade: EndingGrade = EndingGrade.BITTER

    @model_validator(mode="after")
    def validate_grading(self) -> "EndingsTuning":
        weights = (
            self.weight_position
            + self.weight_stability
            + self.weight_treasury
            + self.weight_will
            + self.weight_strain
        )
        if weights != FULL_SHARE_PERCENT:
            raise ValueError("grade weights must sum to 100")
        thresholds = self.grade_thresholds
        if len(thresholds) != GRADE_THRESHOLD_COUNT:
            raise ValueError("grade_thresholds needs exactly three entries")
        if thresholds != sorted(set(thresholds)):
            raise ValueError("grade_thresholds must be strictly increasing")
        if self.vassal_best_grade == EndingGrade.PYRRHIC:
            raise ValueError("vassal_best_grade must be a score tier")
        return self
