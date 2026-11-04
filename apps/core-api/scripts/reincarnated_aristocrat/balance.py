"""Every tunable number of the scenario. All values are placeholders to be tuned
while playtesting; nothing else in the package hard-codes a balance number.
"""

from dataclasses import dataclass

DAYS_PER_YEAR = 365
MONTH_DAYS = 30
DAYS_PER_TURN = 15
TIME_COST_DAYS = {"short": 15, "long": 45, "journey": 75}

ENGAGEMENT_DAY = 3 * DAYS_PER_YEAR
ILLNESS_DAY = 4 * DAYS_PER_YEAR
DEATH_DAY = 1650
COURAN_DAY = 2100
FIRST_BIRTHDAY_AGE = 7
LAST_BIRTHDAY_AGE = 15

TRAIN_LOW_BAND_LIMIT = 60
TRAIN_BIG_GAIN = 2
TRAIN_SMALL_GAIN = 1
TRAIN_BIG_COST = (8, 2)
TRAIN_SMALL_COST = (12, 3)
ARMY_PER_TRAINING = 1
ARMY_TRAINED_STATS = ("leadership", "prowess")

RECRUIT_START_LOYALTY = 50
RECRUIT_STANDING = 2
ARMY_VALUE = {
    "ritsu": 6,
    "charlotte": 5,
    "rosell": 3,
    "lysia": 0,
    "mireille": 4,
    "fahm": 3,
}

BASE_INCOME = 14
INCOME_BONUS = 4
INCOME_PENALTY = 4
UPKEEP_PER_RETAINER = 2
BASE_RESOURCES = 3
LOW_RESOURCES_INCOME = 1
HIGH_BAND = 60
LOW_BAND = 30
UNPAID_BELOW = 10
DISTRESS_BELOW = 15
FEAR_DECAY = 1
UNPAID_LOYALTY_LOSS = 2

COMPETENCE_UP = 2
COMPETENCE_DOWN = 2
COMPETENCE_GOODWILL_STEP = 1
COMPETENCE_DEBT_LOSS = 3
COMPETENCE_RICH_FUNDS = 100

WARNING_AMBITION = 60
WARNING_LOYALTY = 35
RECOVERY_LOYALTY = 50
BETRAYAL_LOYALTY = 20
COUP_COMPETENCE = 25
BETRAYAL_FUNDS_LOSS = 5

WIN_STANDING = 40
WIN_CONTROL = 50
WIN_RESOURCES = 40
WIN_FUNDS = 100
WIN_ARMY = 25
WIN_RECRUITS = 4
WIN_COMPETENCE = 60
FEAR_WIN_FEAR = 60
FEAR_WIN_GOODWILL = 40
RUIN_MONTHS = 3
COLLAPSE_ARMY = 10
COLLAPSE_GRACE_DAYS = 120
TIMEOUT_TURNS = 300


@dataclass(frozen=True)
class Reaction:
    sheet_field: str
    is_at_least: bool
    threshold: int
    stat: str
    delta: int


@dataclass(frozen=True)
class PolicySpec:
    funds: int = 0
    resources: int = 0
    once: tuple[tuple[str, int], ...] = ()
    monthly: tuple[tuple[str, int], ...] = ()


POLICY_SPECS: dict[str, PolicySpec] = {
    "tax_relief": PolicySpec(once=(("sheet.goodwill", 10),), monthly=(("funds", -5),)),
    "farmland_development": PolicySpec(funds=40, monthly=(("resources", 2),)),
    "militia_levy": PolicySpec(
        funds=15,
        once=(("army_strength", 8), ("sheet.goodwill", -8), ("control", -4)),
        monthly=(("funds", -3),),
    ),
    "fortification": PolicySpec(funds=35, resources=10, once=(("control", 10),)),
    "talent_search": PolicySpec(funds=30, once=(("standing", 5),)),
    "strict_law": PolicySpec(
        funds=10,
        once=(("control", 12), ("sheet.fear", 10), ("sheet.goodwill", -8)),
    ),
}

TRAIT_REACTIONS: dict[str, tuple[Reaction, ...]] = {
    "ambitious": (
        Reaction("competence", True, 55, "loyalty", 2),
        Reaction("competence", False, 30, "loyalty", -2),
        Reaction("competence", False, 30, "ambition", 2),
        Reaction("fear", True, 60, "ambition", 1),
        Reaction("fear", True, 60, "loyalty", -1),
    ),
    "devoted": (
        Reaction("goodwill", True, 0, "loyalty", 1),
        Reaction("goodwill", True, 60, "loyalty", 1),
        Reaction("goodwill", False, 25, "loyalty", -3),
    ),
    "proud": (
        Reaction("goodwill", False, 35, "loyalty", -2),
        Reaction("goodwill", False, 35, "ambition", 1),
        Reaction("fear", True, 60, "loyalty", -2),
        Reaction("fear", True, 60, "ambition", 2),
        Reaction("competence", True, 60, "loyalty", 1),
    ),
    "timid": (
        Reaction("fear", True, 60, "loyalty", 1),
        Reaction("fear", True, 60, "ambition", -1),
        Reaction("fear", True, 60, "courage", -1),
        Reaction("goodwill", True, 60, "courage", 1),
    ),
    "pragmatic": (
        Reaction("competence", True, 55, "loyalty", 2),
        Reaction("competence", False, 30, "loyalty", -2),
    ),
    "idealist": (
        Reaction("goodwill", True, 60, "loyalty", 2),
        Reaction("goodwill", True, 60, "courage", 1),
        Reaction("goodwill", False, 35, "loyalty", -3),
        Reaction("fear", True, 60, "loyalty", -2),
    ),
}
