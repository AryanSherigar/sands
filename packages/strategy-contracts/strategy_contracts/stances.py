from enum import Enum

from pydantic import Field, field_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import StanceId
from strategy_contracts.limits import MAX_NAME_CHARS, MAX_TEXT_CHARS

MIN_STANCE_SHIFT = -3
MAX_STANCE_SHIFT = 3
MAX_CUSTOM_STANCES = 8


class ScoreCategory(str, Enum):
    ATTACK = "attack"
    EXPAND = "expand"
    BUILD = "build"
    ALLY = "ally"
    HOARD = "hoard"


class StanceDefinition(StrictModel):
    id: StanceId
    name: str = Field(min_length=1, max_length=MAX_NAME_CHARS)
    description: str = Field(default="", max_length=MAX_TEXT_CHARS)
    shifts: dict[ScoreCategory, int]

    @field_validator("shifts")
    @classmethod
    def validate_shift_range(
        cls, shifts: dict[ScoreCategory, int]
    ) -> dict[ScoreCategory, int]:
        for category, value in shifts.items():
            if not MIN_STANCE_SHIFT <= value <= MAX_STANCE_SHIFT:
                raise ValueError(f"shift on {category.value} must be within range")
        return shifts


def _stance(
    stance_id: str, name: str, description: str, **shifts: int
) -> StanceDefinition:
    return StanceDefinition(
        id=stance_id,
        name=name,
        description=description,
        shifts={ScoreCategory(category): value for category, value in shifts.items()},
    )


BUILTIN_STANCES: tuple[StanceDefinition, ...] = (
    _stance(
        "rebuild",
        "Rebuild",
        "recover strength after losses before risking another fight",
        build=3,
        hoard=2,
        attack=-2,
        expand=-1,
    ),
    _stance(
        "court_ally",
        "Court an ally",
        "seek friends and pacts to secure the realm",
        ally=3,
        attack=-1,
    ),
    _stance(
        "revenge_on_player",
        "Revenge on the player",
        "strike back at the player for past wrongs",
        attack=3,
        ally=-1,
        hoard=-1,
    ),
    _stance(
        "expand",
        "Expand",
        "take new land while the chance is there",
        expand=3,
        attack=2,
        hoard=-1,
    ),
    _stance(
        "turtle",
        "Turtle",
        "hold the borders and avoid risk",
        build=1,
        hoard=2,
        attack=-3,
        expand=-2,
    ),
)
