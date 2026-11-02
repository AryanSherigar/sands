from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from strategy_contracts.base import StrictModel

DEFAULT_JUDGMENT_COOLDOWN_TURNS = 6
DEFAULT_JUDGMENT_SENTENCE_TURNS = 6


class JudgmentSubjectKind(str, Enum):
    CAPTIVE = "captive"
    GOVERNOR = "governor"


class JudgmentVerdict(str, Enum):
    RELEASE = "release"
    EXILE = "exile"
    IMPRISON = "imprison"
    EXECUTE = "execute"


class JudgmentNuance(str, Enum):
    WITH_WARNING = "with_warning"
    UNDER_OATH = "under_oath"
    WITH_PARDON = "with_pardon"
    WITH_FINE = "with_fine"
    BEYOND_BORDER = "beyond_border"
    STRIPPED_OF_TITLE = "stripped_of_title"
    WITH_FAMILY = "with_family"
    WITH_PRICE_ON_RETURN = "with_price_on_return"
    IN_REGION = "in_region"
    IN_CAPITAL = "in_capital"
    FOR_A_TERM = "for_a_term"
    FOR_LIFE = "for_life"
    QUIETLY = "quietly"
    PUBLICLY = "publicly"
    SWIFTLY = "swiftly"
    WITH_LAST_WORD = "with_last_word"


class AdvisorStance(str, Enum):
    MERCY = "mercy"
    IRON = "iron"
    NEUTRAL = "neutral"


NUANCES_BY_VERDICT: dict[JudgmentVerdict, tuple[JudgmentNuance, ...]] = {
    JudgmentVerdict.RELEASE: (
        JudgmentNuance.WITH_WARNING,
        JudgmentNuance.UNDER_OATH,
        JudgmentNuance.WITH_PARDON,
        JudgmentNuance.WITH_FINE,
    ),
    JudgmentVerdict.EXILE: (
        JudgmentNuance.BEYOND_BORDER,
        JudgmentNuance.STRIPPED_OF_TITLE,
        JudgmentNuance.WITH_FAMILY,
        JudgmentNuance.WITH_PRICE_ON_RETURN,
    ),
    JudgmentVerdict.IMPRISON: (
        JudgmentNuance.IN_REGION,
        JudgmentNuance.IN_CAPITAL,
        JudgmentNuance.FOR_A_TERM,
        JudgmentNuance.FOR_LIFE,
    ),
    JudgmentVerdict.EXECUTE: (
        JudgmentNuance.QUIETLY,
        JudgmentNuance.PUBLICLY,
        JudgmentNuance.SWIFTLY,
        JudgmentNuance.WITH_LAST_WORD,
    ),
}


class JudgmentOutcome(StrictModel):
    kind: Literal["judgment"] = "judgment"
    verdict: JudgmentVerdict
    nuance: JudgmentNuance | None = None

    @model_validator(mode="after")
    def validate_nuance_belongs_to_verdict(self) -> "JudgmentOutcome":
        if (
            self.nuance is not None
            and self.nuance not in NUANCES_BY_VERDICT[self.verdict]
        ):
            raise ValueError(
                f"nuance '{self.nuance.value}' does not belong to verdict "
                f"'{self.verdict.value}'"
            )
        return self


class JudgmentOption(StrictModel):
    verdict: JudgmentVerdict
    nuances: list[JudgmentNuance] = Field(default_factory=list)


class JudgmentSpec(StrictModel):
    kind: Literal["judgment"] = "judgment"
    subject_kind: JudgmentSubjectKind
    options: list[JudgmentOption]


class JudgmentTuning(StrictModel):
    is_enabled: bool = False
    cooldown_turns: int = Field(default=DEFAULT_JUDGMENT_COOLDOWN_TURNS, ge=1)
    sentence_turns: int = Field(default=DEFAULT_JUDGMENT_SENTENCE_TURNS, ge=1)
