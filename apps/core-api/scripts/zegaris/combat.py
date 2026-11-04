"""Authored one-on-one encounters for the existing deterministic combat system.

Every number here is the author's tuning call, not canon. Zero health is never
death: each encounter has a non-fatal authored defeat outcome and no ending.
"""

from scripts.seeding.expr import Expression, all_of, eq
from scripts.zegaris.ids import entity_ref
from scripts.zegaris.schema import PLAYER_MAX_HEALTH

TRELIUM_TAG = "trelium"
PLAYER_ID = "player"
OPPONENT_ID = "opponent"
RECOVERY_HEALTH = 15


def _player(attack: int, tags: tuple[str, ...] = ()) -> dict[str, object]:
    return {
        "actor_id": PLAYER_ID,
        "side": "player",
        "max_health": PLAYER_MAX_HEALTH,
        "health": PLAYER_MAX_HEALTH,
        "attack": attack,
        "armor": 2,
        "speed": 5,
        "accuracy": 60,
        "luck": 40,
        "attack_tags": list(tags),
    }


def _opponent(
    health: int,
    attack: int,
    armor: int,
    speed: int,
    accuracy: int,
    required_tag: str | None = None,
) -> dict[str, object]:
    opponent: dict[str, object] = {
        "actor_id": OPPONENT_ID,
        "side": "opponent",
        "max_health": health,
        "health": health,
        "attack": attack,
        "armor": armor,
        "speed": speed,
        "accuracy": accuracy,
        "luck": 30,
    }
    if required_tag is not None:
        opponent["required_attack_tag"] = required_tag
    return opponent


def _recover(outcome_id: str, location_slug: str | None) -> dict[str, object]:
    outcome: dict[str, object] = {
        "id": outcome_id,
        "kind": "recover",
        "health": RECOVERY_HEALTH,
    }
    if location_slug is not None:
        outcome["location_id"] = entity_ref(location_slug)
    return outcome


def _at(location_slug: str) -> Expression:
    return eq("current_location_id", entity_ref(location_slug))


def _encounter(
    encounter_id: str,
    title: str,
    start_condition: Expression,
    player: dict[str, object],
    opponent: dict[str, object],
    recovery: dict[str, object],
) -> dict[str, object]:
    return {
        "encounter_id": encounter_id,
        "title": title,
        "start_condition": start_condition,
        "player": player,
        "opponent": opponent,
        "outcomes": [recovery],
        "fallback_outcome_id": recovery["id"],
    }


def encounters() -> list[dict[str, object]]:
    return [
        _encounter(
            "tavern_brawl",
            "Brawl with a drunk Westerner",
            _at("owls_respite"),
            _player(8),
            _opponent(14, 5, 0, 3, 50),
            _recover("beaten_bloody", None),
        ),
        _encounter(
            "gate_templar",
            "A Black Templar at the gate",
            _at("gate_of_the_unsworn"),
            _player(8),
            _opponent(22, 8, 4, 6, 60),
            _recover("cast_out_to_the_shallows", "blind_shallows"),
        ),
        _encounter(
            "pursuit_templar",
            "Templars hunt you down",
            all_of(eq("world.tithe", "aftermath")),
            _player(8),
            _opponent(30, 11, 5, 6, 65),
            _recover("slipped_away_in_the_chaos", "east_road"),
        ),
        _encounter(
            "fissure_abomination",
            "Something crawls from the fissure",
            _at("fissure_depths"),
            _player(8, (TRELIUM_TAG,)),
            _opponent(26, 8, 3, 4, 55, TRELIUM_TAG),
            _recover("dragged_back_to_the_tally_gate", "tally_gate"),
        ),
    ]


def fantasy_combat() -> dict[str, object]:
    return {"encounters": encounters()}
