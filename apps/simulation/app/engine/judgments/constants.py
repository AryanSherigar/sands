from strategy_contracts.judgment import JudgmentNuance, JudgmentVerdict

JUDGMENT_CAUSE_MERCY = "judgment_mercy"
JUDGMENT_CAUSE_CRUELTY = "judgment_cruelty"
JUDGMENT_OPINION_FADE_PER_TURN = 1
MEMORY_KIND_PREFIX = "judgment_"
MEMORY_WEIGHT = 4
MAX_ADVISORS = 2
JUDGMENT_EXCHANGE_CAP = 6

BASE_OPINION: dict[JudgmentVerdict, int] = {
    JudgmentVerdict.RELEASE: 8,
    JudgmentVerdict.EXILE: -4,
    JudgmentVerdict.IMPRISON: -4,
    JudgmentVerdict.EXECUTE: -20,
}
BASE_MERCY_SCORE: dict[JudgmentVerdict, int] = {
    JudgmentVerdict.RELEASE: 10,
    JudgmentVerdict.EXILE: 0,
    JudgmentVerdict.IMPRISON: 0,
    JudgmentVerdict.EXECUTE: -15,
}
WITNESS_GOVERNOR_SHIFT: dict[JudgmentVerdict, int] = {
    JudgmentVerdict.RELEASE: 3,
    JudgmentVerdict.EXILE: -2,
    JudgmentVerdict.IMPRISON: -2,
    JudgmentVerdict.EXECUTE: -5,
}
NUANCE_OPINION: dict[JudgmentNuance, int] = {
    JudgmentNuance.WITH_WARNING: 0,
    JudgmentNuance.UNDER_OATH: 2,
    JudgmentNuance.WITH_PARDON: 4,
    JudgmentNuance.WITH_FINE: -3,
    JudgmentNuance.BEYOND_BORDER: 0,
    JudgmentNuance.STRIPPED_OF_TITLE: -2,
    JudgmentNuance.WITH_FAMILY: 3,
    JudgmentNuance.WITH_PRICE_ON_RETURN: -2,
    JudgmentNuance.IN_REGION: 0,
    JudgmentNuance.IN_CAPITAL: -2,
    JudgmentNuance.FOR_A_TERM: 2,
    JudgmentNuance.FOR_LIFE: -4,
    JudgmentNuance.QUIETLY: 6,
    JudgmentNuance.PUBLICLY: -6,
    JudgmentNuance.SWIFTLY: 2,
    JudgmentNuance.WITH_LAST_WORD: 3,
}
NUANCE_MERCY_SCORE: dict[JudgmentNuance, int] = {
    JudgmentNuance.WITH_PARDON: 5,
    JudgmentNuance.WITH_FINE: -5,
    JudgmentNuance.WITH_FAMILY: 3,
    JudgmentNuance.WITH_PRICE_ON_RETURN: -3,
    JudgmentNuance.FOR_LIFE: -5,
    JudgmentNuance.QUIETLY: 5,
    JudgmentNuance.PUBLICLY: -5,
    JudgmentNuance.SWIFTLY: 2,
    JudgmentNuance.WITH_LAST_WORD: 3,
}
