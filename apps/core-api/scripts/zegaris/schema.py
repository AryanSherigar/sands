"""The scenario's state_schema.

Visible: health, coins, energy, inventory and the retrieval mission stage (the
fantasy reader reads these paths). Hidden: the Grand Tithe stage, Zegaris
access and the intent flags the narrator sets for conditions to act on. The
Tithe stage is hidden and opaquely named so the schema itself reveals nothing.
"""

from scripts.seeding.fields import FieldDef, Schema, enum, flatten_schema, group, number

PLAYER_MAX_HEALTH = 30
COIN_CEILING = 9999
STARTING_COINS = 10
ENERGY_MAX = 100
INITIAL_ENERGY = 70
NO_VALUE = ""
INTENT_GROUP = "intent"

RETRIEVAL_STAGES = ("offered", "accepted", "body_recovered", "cremated", "rewarded")
TITHE_STAGES = ("offered", "hired", "hauling", "eclipse", "aftermath")
ACCESS_LEVELS = ("none", "badge", "escort")
TITHE_STEPS = (NO_VALUE, "hired", "hauling", "eclipse", "aftermath")
ACCESS_STEPS = (NO_VALUE, "badge", "escort", "revoked")


def _counter(label: str, fact: str, high: int, initial: int) -> FieldDef:
    field = number(0, high, initial)
    field["label"] = label
    field["narrator_fact"] = fact
    return field


def _player_group() -> FieldDef:
    return group(
        {
            "health": _counter(
                "Health", "The player's health", PLAYER_MAX_HEALTH, PLAYER_MAX_HEALTH
            ),
            "coins": _counter(
                "Coins", "Coins in the player's purse", COIN_CEILING, STARTING_COINS
            ),
            "energy": _counter(
                "Energy", "The player's energy", ENERGY_MAX, INITIAL_ENERGY
            ),
            "inventory": {"type": "list", "item_type": "entity_ref"},
        },
        is_hidden=False,
    )


def _quests_group() -> FieldDef:
    stage = enum(RETRIEVAL_STAGES, "offered")
    stage["label"] = "Ruinkrag bounty"
    return group({"retrieval": group({"stage": stage}, is_hidden=False)}, False)


def build_state_schema() -> Schema:
    return {
        "player": _player_group(),
        "quests": _quests_group(),
        "world": group(
            {
                "tithe": enum(TITHE_STAGES, "offered"),
                "access": enum(ACCESS_LEVELS, "none"),
            }
        ),
        INTENT_GROUP: group(
            {
                "tithe_step": enum(TITHE_STEPS, NO_VALUE),
                "access_step": enum(ACCESS_STEPS, NO_VALUE),
            }
        ),
    }


def flat_fields() -> dict[str, FieldDef]:
    return flatten_schema(build_state_schema())
