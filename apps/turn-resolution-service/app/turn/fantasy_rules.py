import copy
import math

from app.exceptions.fantasy_exceptions import FantasyActionError


def _record(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise FantasyActionError("Fantasy state or configuration is invalid.")
    return value


def _number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _validate_profile(config: dict[str, object]) -> None:
    if (
        type(config.get("version")) is not int
        or config["version"] != 1
        or config.get("profile") != "zegaris"
    ):
        raise FantasyActionError("Fantasy mechanics are unavailable.")


def _at_location(state: dict[str, object], config: dict[str, object], key: str) -> None:
    location = _record(config.get("locations")).get(key)
    if (
        not isinstance(location, str)
        or not location
        or state.get("current_location_id") != location
    ):
        raise FantasyActionError("This action is not available here.")


def _coins(player: dict[str, object]) -> int:
    coins = player.get("coins")
    if type(coins) is not int or coins < 0:
        raise FantasyActionError("The coin balance is invalid.")
    return coins


def _rest(state: dict[str, object], config: dict[str, object]) -> None:
    _at_location(state, config, "inn")
    player = _record(state.get("player"))
    maximum = config.get("energy_max")
    initial = config.get("initial_energy")
    cost = config.get("rest_cost")
    if (
        not _number(maximum)
        or maximum <= 0
        or not _number(initial)
        or not 0 <= initial <= maximum
    ):
        raise FantasyActionError("Rest is not configured.")
    if type(cost) is not int or cost != 5:
        raise FantasyActionError("Rest is not configured.")
    coins = _coins(player)
    if coins < cost:
        raise FantasyActionError("You do not have enough coins.")
    player["coins"] = coins - cost
    player["energy"] = maximum


def _claim_reward(state: dict[str, object], config: dict[str, object]) -> None:
    _at_location(state, config, "quest_giver")
    player = _record(state.get("player"))
    quest = _record(_record(state.get("quests")).get("retrieval"))
    reward = config.get("bounty_reward")
    if type(reward) is not int or reward < 0 or quest.get("stage") != "cremated":
        raise FantasyActionError("The reward is not available.")
    player["coins"] = _coins(player) + reward
    quest["stage"] = "rewarded"


def resolve_fantasy_action(
    state: dict[str, object], config: dict[str, object], action_id: str
) -> dict[str, object]:
    """Return a new candidate; caller must validate and atomically commit it."""
    _validate_profile(config)
    candidate = copy.deepcopy(state)
    if action_id == "rest":
        _rest(candidate, config)
    elif action_id == "claim_retrieval_reward":
        _claim_reward(candidate, config)
    else:
        raise FantasyActionError("Unknown fantasy action.")
    return candidate


def _mission_inventory(state: dict[str, object]) -> list[str]:
    inventory = _record(state.get("player")).get("inventory")
    if not isinstance(inventory, list) or not all(
        isinstance(item, str) for item in inventory
    ):
        raise FantasyActionError("The inventory is invalid.")
    return inventory


def resolve_mission_event(
    state: dict[str, object], config: dict[str, object], event: str
) -> dict[str, object]:
    """Return a legal one-step mission transition without mutating the input."""
    _validate_profile(config)
    transitions = {
        "accept_retrieval": ("offered", "accepted", "quest_giver"),
        "recover_body": ("accepted", "body_recovered", "recovery"),
        "cremate_body": ("body_recovered", "cremated", "cremation"),
    }
    transition = transitions.get(event)
    if transition is None:
        raise FantasyActionError("Unknown mission event.")
    previous, following, location = transition
    _at_location(state, config, location)
    candidate = copy.deepcopy(state)
    quest = _record(_record(candidate.get("quests")).get("retrieval"))
    if quest.get("stage") != previous:
        raise FantasyActionError("That mission event is not available.")
    corpse = config.get("corpse_item_id")
    if not isinstance(corpse, str) or not corpse:
        raise FantasyActionError("The mission is not configured.")
    inventory = _mission_inventory(candidate)
    if event == "recover_body":
        if corpse in inventory:
            raise FantasyActionError("The item is already carried.")
        inventory.append(corpse)
    if event == "cremate_body":
        if corpse not in inventory:
            raise FantasyActionError("The item is not carried.")
        inventory.remove(corpse)
    quest["stage"] = following
    return candidate


def protects_transition(
    before: dict[str, object], after: dict[str, object], config: object
) -> bool:
    """Detect any untrusted change to profile-owned values, including parent writes."""
    if (
        not isinstance(config, dict)
        or type(config.get("version")) is not int
        or config.get("version") != 1
        or config.get("profile") != "zegaris"
    ):
        return False

    def values(state: dict[str, object]) -> tuple[object, object, object, int]:
        player = state.get("player") if isinstance(state.get("player"), dict) else {}
        quests = state.get("quests") if isinstance(state.get("quests"), dict) else {}
        retrieval = (
            quests.get("retrieval") if isinstance(quests.get("retrieval"), dict) else {}
        )
        inventory = (
            player.get("inventory") if isinstance(player.get("inventory"), list) else []
        )
        corpse = config.get("corpse_item_id")
        return (
            player.get("coins"),
            player.get("energy"),
            retrieval.get("stage"),
            inventory.count(corpse),
        )

    return values(before) != values(after)
