"""The scenario's state_schema (data doc §5) and helpers to inspect it.

Field shapes follow apps/turn-resolution-service/app/models/game_state.py:
number (min/max), boolean, string, enum (string `options`), entity_ref, list,
and nested `object` with `fields`. Everything the player must not read is
`hidden: true`; rule statuses and flags are owned by the `rule_sheet` tool and
the player's position by the map system, so neither is declared here.
"""

from scripts.night_desk import hints
from scripts.seeding.fields import (  # noqa: F401
    FieldDef,
    Schema,
    enum,
    flag,
    flatten_schema,
    group,
    number,
)

SANITY_START = 85
SANITY_FLOOR = -100
SANITY_CEILING = 100
SHIFT_MINUTES_MAX = 480
WRONG_ENTRIES_MAX = 9
DIFFERENCE_MAX = 10
UNSIGNED_MAX = 3
READS_AFTER_TWO_MAX = 2
RECORDS_VISITS_MAX = 9
COUNTER_MAX = 99
SEED_CHOICES = ("r4", "r6")

RULE_IDS = ("r1", "r2", "r3", "r4", "r6", "r6_block", "r7", "r8")
INITIALLY_REVEALED = ("r1", "r2", "r3", "r4")
VISITOR_IDS = ("v1", "v2", "v3")
FRAGMENT_SLOTS = ("act1", "act2", "act3")
FRAGMENT_IDS = ("f1", "f2", "f3", "f4", "f5", "f6")
COUNT_STATES = ("", "pending", "signed", "left", "timeout")
YES_NO_STATES = ("", "pending", "yes", "no")
EVENT_NAMES = ("stairwell", "elevator")
VISITED_FLAGS = ("print_room", "elevator_lobby", "cabin_14")


def counter() -> FieldDef:
    return number(0, COUNTER_MAX, 0)


def _check_fields() -> Schema:
    return {
        "lamp": enum(("", "pending", "held_still", "moved", "entered", "timeout"), ""),
        "phone": enum(
            ("", "pending", "let_ring", "picked_up", "unplugged", "timeout"), ""
        ),
        "voicemail": enum(YES_NO_STATES, ""),
        "drawer": enum(YES_NO_STATES, ""),
    }


def _count_fields() -> Schema:
    return {
        "wrong_entries": number(0, WRONG_ENTRIES_MAX, 0),
        "difference": number(1, DIFFERENCE_MAX, 1),
        "c1": enum(COUNT_STATES, ""),
        "c2": enum(COUNT_STATES, ""),
        "c3": enum(COUNT_STATES, ""),
        "unsigned": number(0, UNSIGNED_MAX, 0),
        "reads_after_two": number(0, READS_AFTER_TWO_MAX, 0),
    }


def _flag_fields() -> Schema:
    return {
        "cabin_entered": flag(),
        "line14_lit": flag(),
        "hum": enum(("idle", "done"), "idle"),
        "escalations": counter(),
    }


def _fragment_fields() -> Schema:
    fields: Schema = {slot: enum(("", *FRAGMENT_IDS), "") for slot in FRAGMENT_SLOTS}
    fields["poster"] = enum(("locked", "shown"), "locked")
    return fields


def _visited_fields() -> Schema:
    fields: Schema = {"records_room": number(0, RECORDS_VISITS_MAX, 0)}
    fields["last"] = {"type": "string", "initial": "night_desk"}
    fields.update({name: flag() for name in VISITED_FLAGS})
    return fields


def _lamp_field() -> FieldDef:
    lamp = enum(("on", "out"), "on")
    lamp["narrator_fact"] = "Cabin 14 lamp"
    return lamp


def _world_fields() -> Schema:
    seed = enum(SEED_CHOICES, "r6")
    seed["initial_random"] = list(SEED_CHOICES)
    return {
        "player": group(
            {"inventory": {"type": "list", "item_type": "entity_ref"}}, False
        ),
        "cabin": group({"lamp": _lamp_field()}),
        "seed": group({"false_rule": seed}),
    }


def _visible_fields() -> Schema:
    clock = number(0, SHIFT_MINUTES_MAX, 0)
    clock["label"] = "Shift"
    clock["display"] = hints.clock_hint("sanity")
    tier = enum(("uneasy", "tense", "dread", "breaking"), "uneasy")
    tier["label"] = "Tension"
    tier["display"] = hints.tension_hint()
    sanity = number(SANITY_FLOOR, SANITY_CEILING, SANITY_START)
    sanity["label"] = "Sanity"
    sanity["display"] = hints.sanity_hint()
    return {"shift_minutes": clock, "tension_tier": tier, "sanity": sanity}


def _hidden_counters() -> Schema:
    violations = counter()
    violations["hidden"] = True
    return {"violations_count": violations}


def build_state_schema() -> Schema:
    return {
        **_visible_fields(),
        **_hidden_counters(),
        **_world_fields(),
        "visit": group(
            {
                "pending": enum(("", *VISITOR_IDS), ""),
                "result": enum(("", "told", "wall", "other", "rejected", "none"), ""),
                "present": enum(("", *VISITOR_IDS), ""),
                "turns_present": counter(),
            }
        ),
        "count": group(_count_fields()),
        "check": group(_check_fields()),
        "flags": group(_flag_fields()),
        "events": group({name: flag() for name in EVENT_NAMES}),
        "visited": group(_visited_fields()),
        "dwell": group({"alcove": counter()}),
        "fragments": group(_fragment_fields()),
    }
