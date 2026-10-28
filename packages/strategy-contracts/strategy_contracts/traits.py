from enum import Enum

from pydantic import Field, field_validator

from strategy_contracts.base import StrictModel
from strategy_contracts.ids import TraitId
from strategy_contracts.limits import MAX_TEXT_CHARS

MIN_TRAIT_EFFECT = -3
MAX_TRAIT_EFFECT = 3


class TraitAxis(str, Enum):
    AGGRESSION = "aggression"
    HONOR = "honor"
    CAUTION = "caution"
    CUNNING = "cunning"
    PRIDE = "pride"
    CRUELTY = "cruelty"
    GREED = "greed"
    ZEAL = "zeal"
    TRUST = "trust"


class TraitDefinition(StrictModel):
    id: TraitId
    name: str
    description: str = Field(default="", max_length=MAX_TEXT_CHARS)
    effects: dict[TraitAxis, int]

    @field_validator("effects")
    @classmethod
    def validate_effect_range(
        cls, effects: dict[TraitAxis, int]
    ) -> dict[TraitAxis, int]:
        for axis, value in effects.items():
            if not MIN_TRAIT_EFFECT <= value <= MAX_TRAIT_EFFECT:
                raise ValueError(f"effect on {axis.value} must be within trait range")
        return effects


def _trait(
    trait_id: str, name: str, description: str, **effects: int
) -> TraitDefinition:
    return TraitDefinition(
        id=trait_id,
        name=name,
        description=description,
        effects={TraitAxis(axis): value for axis, value in effects.items()},
    )


BUILTIN_TRAITS: tuple[TraitDefinition, ...] = (
    _trait(
        "honorable",
        "Honorable",
        "keeps their word and expects the same; scorns tricks",
        honor=3,
        cruelty=-1,
        cunning=-1,
    ),
    _trait(
        "treacherous",
        "Treacherous",
        "treats promises as tools and assumes others do too",
        honor=-3,
        cunning=2,
        trust=-1,
    ),
    _trait(
        "proud",
        "Proud",
        "hears weakness in any request and is slow to concede",
        pride=3,
        caution=-1,
    ),
    _trait(
        "wrathful",
        "Wrathful",
        "quick to anger and eager for a fight",
        aggression=3,
        pride=1,
        caution=-2,
    ),
    _trait(
        "cautious",
        "Cautious",
        "weighs every risk and prefers safe, lasting arrangements",
        caution=3,
        aggression=-2,
    ),
    _trait(
        "pragmatic",
        "Pragmatic",
        "judges an offer by its worth, not its pride",
        greed=1,
        pride=-2,
        zeal=-1,
    ),
    _trait(
        "cunning",
        "Cunning",
        "looks for the hidden angle and distrusts easy offers",
        cunning=3,
        trust=-1,
    ),
    _trait(
        "paranoid",
        "Paranoid",
        "expects betrayal and wants guarantees",
        trust=-3,
        caution=2,
        cunning=1,
    ),
    _trait(
        "trusting",
        "Trusting",
        "takes people at their word and warms to goodwill",
        trust=3,
        cunning=-2,
    ),
    _trait(
        "naive",
        "Naive",
        "believes fair-sounding offers and misses the trap",
        trust=2,
        cunning=-3,
    ),
    _trait(
        "stubborn",
        "Stubborn",
        "digs in once a position is taken",
        pride=2,
        caution=-1,
        cunning=-1,
    ),
    _trait(
        "calculating",
        "Calculating",
        "bargains coldly and keeps count of every concession",
        cunning=2,
        caution=1,
        pride=-1,
    ),
    _trait(
        "cruel",
        "Cruel",
        "has little pity and respects only strength",
        cruelty=3,
        honor=-2,
        aggression=1,
    ),
    _trait(
        "zealot",
        "Zealot",
        "sees the world through faith and distrusts unbelievers",
        zeal=3,
        aggression=1,
        trust=-1,
    ),
)
