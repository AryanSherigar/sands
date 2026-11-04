"""The pinned `fantasy_mechanics` profile: class loadouts and mission mapping.

The numbers below are the author's calls, not canon: the canon fixes only the
10 starting coins and the 5-coin rest.
"""

from scripts.zegaris.ids import entity_ref
from scripts.zegaris.schema import ENERGY_MAX, INITIAL_ENERGY

REST_COST = 5
BOUNTY_REWARD = 25
CORPSE_SLUG = "fallen_soldiers_body"

CLASS_LOADOUTS: dict[str, tuple[str, ...]] = {
    "disgraced_knight": ("steel_longsword", "battered_iron_armor"),
    "rogue_apprentice": (
        "forbidden_manuscript",
        "utility_dagger",
        "ink_and_stylus",
        "academy_robes",
    ),
    "fugitive_smuggler": (
        "belt_knives",
        "lockpicks",
        "liquor_flask",
        "leather_travel_clothes",
    ),
    "last_priest": ("iron_mace", "prayer_stole", "silver_reliquary"),
}

LOCATION_MAP = {
    "inn": "owls_respite",
    "quest_giver": "council_hall",
    "recovery": "fissure_depths",
    "cremation": "great_pyres",
}


def fantasy_mechanics() -> dict[str, object]:
    return {
        "version": 1,
        "profile": "zegaris",
        "energy_max": ENERGY_MAX,
        "initial_energy": INITIAL_ENERGY,
        "rest_cost": REST_COST,
        "bounty_reward": BOUNTY_REWARD,
        "corpse_item_id": entity_ref(CORPSE_SLUG),
        "locations": {key: entity_ref(slug) for key, slug in LOCATION_MAP.items()},
        "class_loadouts": {
            key: [entity_ref(slug) for slug in slugs]
            for key, slugs in CLASS_LOADOUTS.items()
        },
    }
