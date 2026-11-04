"""Initialize the explicitly authored Zegaris profile from its pinned snapshot."""

import copy
import math

from app.exceptions.playthrough_exceptions import InvalidSchemaInitialError

CLASS_KEYS = (
    "disgraced_knight",
    "rogue_apprentice",
    "fugitive_smuggler",
    "last_priest",
)
LOCATION_KEYS = ("inn", "quest_giver", "recovery", "cremation")


def _invalid(reason: str) -> None:
    raise InvalidSchemaInitialError("fantasy_mechanics", reason)


def _valid_number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _validate_numbers(config: dict[str, object]) -> None:
    maximum = config.get("energy_max")
    initial = config.get("initial_energy")
    reward = config.get("bounty_reward")
    if maximum is not None and (not _valid_number(maximum) or maximum <= 0):
        _invalid("energy_max must be a positive finite number or null")
    if initial is not None and (
        not _valid_number(initial) or maximum is None or not 0 <= initial <= maximum
    ):
        _invalid("initial_energy must fit within energy_max")
    if type(config.get("rest_cost")) is not int or config["rest_cost"] != 5:
        _invalid("rest_cost must be 5")
    if reward is not None and (type(reward) is not int or reward < 0):
        _invalid("bounty_reward must be a nonnegative integer or null")


def _entity_ids(snapshot: dict[str, object], kind: str) -> set[str]:
    entities = snapshot.get("entities", [])
    if not isinstance(entities, list):
        _invalid("entities must be a list")
    return {
        str(entity.get("entity_id"))
        for entity in entities
        if isinstance(entity, dict) and entity.get("entity_type") == kind
    }


def _validate_references(
    config: dict[str, object], snapshot: dict[str, object]
) -> dict[str, list[str]]:
    locations = config.get("locations")
    loadouts = config.get("class_loadouts")
    item_ids = _entity_ids(snapshot, "item")
    location_ids = _entity_ids(snapshot, "location")
    if not isinstance(locations, dict) or any(
        not isinstance(locations.get(key), str) or locations[key] not in location_ids
        for key in LOCATION_KEYS
    ):
        _invalid("all mapped locations must reference location entities")
    corpse = config.get("corpse_item_id")
    if not isinstance(corpse, str) or corpse not in item_ids:
        _invalid("corpse_item_id must reference an item entity")
    if not isinstance(loadouts, dict):
        _invalid("class_loadouts must be an object")
    for key in CLASS_KEYS:
        items = loadouts.get(key)
        if not isinstance(items, list) or any(
            not isinstance(item, str) or item not in item_ids for item in items
        ):
            _invalid(f"invalid class loadout: {key}")
    return loadouts


def apply_fantasy_setup(
    snapshot: dict[str, object],
    state: dict[str, object],
    setup_values: dict[str, object],
) -> dict[str, object]:
    config = snapshot.get("fantasy_mechanics")
    if (
        not isinstance(config, dict)
        or type(config.get("version")) is not int
        or config.get("version") != 1
        or config.get("profile") != "zegaris"
    ):
        return state
    _validate_numbers(config)
    loadouts = _validate_references(config, snapshot)
    selected = setup_values.get("outlander_class")
    if selected not in CLASS_KEYS:
        _invalid("choose an authored outlander class")
    candidate = copy.deepcopy(state)
    player = candidate.setdefault("player", {})
    if not isinstance(player, dict):
        _invalid("player state must be an object")
    player["coins"] = 10
    player["inventory"] = list(loadouts[selected])
    if config.get("initial_energy") is not None:
        player["energy"] = config["initial_energy"]
    quests = candidate.setdefault("quests", {})
    if not isinstance(quests, dict):
        _invalid("quests state must be an object")
    retrieval = quests.setdefault("retrieval", {})
    if not isinstance(retrieval, dict):
        _invalid("retrieval state must be an object")
    retrieval["stage"] = "offered"
    return candidate
