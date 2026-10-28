from enum import Enum

from pydantic import Field, field_validator

from strategy_contracts.base import StrictModel


class PressureBand(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ShockKind(str, Enum):
    CAPITAL_FALLS = "capital_falls"
    RULER_CAPTURED = "ruler_captured"
    NEW_ENEMY = "new_enemy"
    HOME_ARMY_DESTROYED = "home_army_destroyed"


class HopeSource(str, Enum):
    ALLIED_ARMY = "allied_army"
    SUBSIDY = "subsidy"
    MEDIATION = "mediation"
    RELIEF_ARMY = "relief_army"
    HELD_FORTRESS = "held_fortress"


class RumorTopic(str, Enum):
    WILL = "will"
    STRAIN = "strain"
    RAGE = "rage"
    THREAT = "threat"


DEFAULT_BAND_THRESHOLDS = (20, 40, 60, 80)
DEFAULT_SHOCK_AMOUNTS: dict[ShockKind, int] = {
    ShockKind.CAPITAL_FALLS: 25,
    ShockKind.RULER_CAPTURED: 30,
    ShockKind.NEW_ENEMY: 15,
    ShockKind.HOME_ARMY_DESTROYED: 20,
}
DEFAULT_STALEMATE_TURNS_PER_STRAIN = 2
DEFAULT_SECOND_FRONT_STRAIN = 10
DEFAULT_HOPE_WILL_BONUS = 10
DEFAULT_HUMILIATION_WILL_PER_POINT = 1
DEFAULT_HUMILIATION_CAP = 30
DEFAULT_EXTINCTION_FLOOR = 60
DEFAULT_MEDIATION_TTL_TURNS = 3
DEFAULT_RUMOR_REPORT_PERCENT = 50
DEFAULT_WRONG_HINT_BASE_PERCENT = 40
DEFAULT_ACCEPTANCE_SHIFT_DIVISOR = 10
DEFAULT_DEVASTATION_STEP = 10
DEFAULT_HOPE_CANCEL_TURNS = 3
DEFAULT_RELIEF_ARMY_MIN_MORALE = 50


def _default_band_thresholds() -> list[int]:
    return list(DEFAULT_BAND_THRESHOLDS)


def _default_shock_amounts() -> dict[ShockKind, int]:
    return dict(DEFAULT_SHOCK_AMOUNTS)


class PressureTuning(StrictModel):
    rule_version: str = "pressure-v1"
    band_thresholds: list[int] = Field(default_factory=_default_band_thresholds)
    shock_amounts: dict[ShockKind, int] = Field(default_factory=_default_shock_amounts)
    stalemate_turns_per_strain: int = Field(
        default=DEFAULT_STALEMATE_TURNS_PER_STRAIN, ge=1
    )
    second_front_strain: int = Field(default=DEFAULT_SECOND_FRONT_STRAIN, ge=0)
    hope_will_bonus: int = Field(default=DEFAULT_HOPE_WILL_BONUS, ge=0)
    humiliation_will_per_point: int = Field(
        default=DEFAULT_HUMILIATION_WILL_PER_POINT, ge=0
    )
    humiliation_cap: int = Field(default=DEFAULT_HUMILIATION_CAP, ge=0)
    extinction_floor: int = Field(default=DEFAULT_EXTINCTION_FLOOR, ge=0, le=100)
    mediation_ttl_turns: int = Field(default=DEFAULT_MEDIATION_TTL_TURNS, ge=1)
    rumor_report_percent: int = Field(
        default=DEFAULT_RUMOR_REPORT_PERCENT, ge=0, le=100
    )
    wrong_hint_base_percent: int = Field(
        default=DEFAULT_WRONG_HINT_BASE_PERCENT, ge=0, le=100
    )
    acceptance_shift_divisor: int = Field(
        default=DEFAULT_ACCEPTANCE_SHIFT_DIVISOR, ge=1
    )
    devastation_step: int = Field(default=DEFAULT_DEVASTATION_STEP, ge=1, le=100)
    hope_cancel_turns: int = Field(default=DEFAULT_HOPE_CANCEL_TURNS, ge=0)
    relief_army_min_morale: int = Field(
        default=DEFAULT_RELIEF_ARMY_MIN_MORALE, ge=0, le=100
    )

    @field_validator("band_thresholds")
    @classmethod
    def validate_band_thresholds(cls, thresholds: list[int]) -> list[int]:
        if len(thresholds) != len(PressureBand) - 1:
            raise ValueError("band_thresholds needs one fewer entry than bands")
        if thresholds != sorted(set(thresholds)):
            raise ValueError("band_thresholds must be strictly increasing")
        return thresholds

    @field_validator("shock_amounts")
    @classmethod
    def validate_shock_amounts(
        cls, amounts: dict[ShockKind, int]
    ) -> dict[ShockKind, int]:
        if set(amounts) != set(ShockKind):
            raise ValueError("shock_amounts must define every shock kind")
        if any(amount < 1 for amount in amounts.values()):
            raise ValueError("shock amounts must be at least 1")
        return amounts
