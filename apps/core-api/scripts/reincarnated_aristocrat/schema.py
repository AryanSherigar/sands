"""The scenario's state_schema.

Visible: Ars's age and the five House meters. Hidden (stripped from the client):
Ars's reputation sheet, the clock, the story beats, adopted policies and the
intent flags the narrator sets for conditions to act on. Entity attributes (the
retainers' stats) live on the entities, not here.
"""

from scripts.reincarnated_aristocrat.characters import (
    CHARACTER_SLUGS,
    RECRUITABLE_SLUGS,
)
from scripts.reincarnated_aristocrat.stats import TRAINABLE_STATS
from scripts.seeding.fields import FieldDef, Schema, enum, flag, group, number

ARS_START_AGE = 6
ARS_MAX_AGE = 40
CLOCK_MAX_DAYS = 3650
TURNS_MAX = 999
RECRUIT_MAX = 10
MONTH_COUNTER_MAX = 99
FIRST_INCOME_DAY = 30
PERCENT_MAX = 100
FUNDS_MAX = 999
SHEET_START_GOODWILL = 50
SHEET_START_FEAR = 10
SHEET_START_COMPETENCE = 40

HOUSE_STATS: tuple[tuple[str, str, int, int], ...] = (
    ("funds", "Funds", FUNDS_MAX, 60),
    ("resources", "Resources", PERCENT_MAX, 40),
    ("control", "Control", PERCENT_MAX, 40),
    ("army_strength", "Army Strength", PERCENT_MAX, 5),
    ("standing", "Standing", PERCENT_MAX, 10),
)
POLICIES = (
    "tax_relief",
    "farmland_development",
    "militia_levy",
    "fortification",
    "talent_search",
    "strict_law",
)
BEATS = (
    "engaged",
    "illness_begun",
    "raven_dead",
    "couran_called",
    "fahm_findable",
    "mireille_findable",
    "coup",
)
TIME_COSTS = ("", "short", "long", "journey")
NO_TARGET = ""
INTENT_GROUP = "intent"


def meter(label: str, maximum: int) -> dict[str, object]:
    return {"kind": "meter", "label": label, "clamp_min": 0, "clamp_max": maximum}


def _house_field(label: str, maximum: int, initial: int) -> FieldDef:
    field = number(0, maximum, initial)
    field["label"] = label
    field["display"] = meter(label, maximum)
    field["narrator_fact"] = f"House {label}"
    return field


def _fact_number(initial: int, fact: str, maximum: int = PERCENT_MAX) -> FieldDef:
    field = number(0, maximum, initial)
    field["narrator_fact"] = fact
    return field


def _player_group() -> FieldDef:
    age = number(ARS_START_AGE, ARS_MAX_AGE, ARS_START_AGE)
    age["label"] = "Age"
    age["display"] = meter("Age", ARS_MAX_AGE)
    age["narrator_fact"] = "Ars's age"
    return group({"age": age}, is_hidden=False)


def _sheet_group() -> FieldDef:
    competence = number(0, PERCENT_MAX, SHEET_START_COMPETENCE)
    competence["derived"] = True
    return group(
        {
            "goodwill": _fact_number(
                SHEET_START_GOODWILL, "How well Ars treats his people"
            ),
            "fear": _fact_number(SHEET_START_FEAR, "How much people fear Ars"),
            "competence": competence,
        }
    )


def _time_group() -> FieldDef:
    return group(
        {
            "clock_days": number(0, CLOCK_MAX_DAYS, 0),
            "next_income_day": number(0, CLOCK_MAX_DAYS, FIRST_INCOME_DAY),
            "turns": number(0, TURNS_MAX, 0),
            "recruits": number(0, RECRUIT_MAX, 0),
            "debt_months": number(0, MONTH_COUNTER_MAX, 0),
            "low_resources": number(0, MONTH_COUNTER_MAX, 0),
            "low_control": number(0, MONTH_COUNTER_MAX, 0),
        }
    )


def _intent_group() -> FieldDef:
    return group(
        {
            "appraise_target": enum((NO_TARGET, *CHARACTER_SLUGS), NO_TARGET),
            "recruit_target": enum((NO_TARGET, *RECRUITABLE_SLUGS), NO_TARGET),
            "train_who": enum((NO_TARGET, *RECRUITABLE_SLUGS), NO_TARGET),
            "train_stat": enum((NO_TARGET, *TRAINABLE_STATS), NO_TARGET),
            "adopt_policy": enum((NO_TARGET, *POLICIES), NO_TARGET),
            "time_cost": enum(TIME_COSTS, ""),
        }
    )


def build_state_schema() -> Schema:
    house = {
        key: _house_field(label, high, start) for key, label, high, start in HOUSE_STATS
    }
    return {
        "player": _player_group(),
        **house,
        "sheet": _sheet_group(),
        "time": _time_group(),
        "beats": group({name: flag() for name in BEATS}),
        "policies": group({name: flag() for name in POLICIES}),
        INTENT_GROUP: _intent_group(),
    }
