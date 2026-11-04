import pytest
from app.exceptions.playthrough_exceptions import InvalidSchemaInitialError
from app.services.fantasy_setup import apply_fantasy_setup

CLASSES = ("disgraced_knight", "rogue_apprentice", "fugitive_smuggler", "last_priest")


def snapshot():
    return {
        "fantasy_mechanics": {
            "version": 1,
            "profile": "zegaris",
            "rest_cost": 5,
            "energy_max": 100,
            "initial_energy": 50,
            "bounty_reward": None,
            "corpse_item_id": "corpse",
            "locations": {
                "inn": "inn",
                "quest_giver": "quest",
                "recovery": "recovery",
                "cremation": "cremation",
            },
            "class_loadouts": {name: [name] for name in CLASSES},
        },
        "entities": (
            [
                {"entity_id": name, "entity_type": "item"}
                for name in (*CLASSES, "corpse")
            ]
            + [
                {"entity_id": name, "entity_type": "location"}
                for name in ("inn", "quest", "recovery", "cremation")
            ]
        ),
    }


@pytest.mark.parametrize("class_name", CLASSES)
def test_class_setup_preserves_state_and_pins_equipment(class_name):
    state = {"player": {"coins": 10}, "other": True}
    result = apply_fantasy_setup(snapshot(), state, {"outlander_class": class_name})
    assert result["player"] == {"coins": 10, "energy": 50, "inventory": [class_name]}
    assert state == {"player": {"coins": 10}, "other": True}
    assert result["quests"]["retrieval"]["stage"] == "offered"


def test_unknown_profile_does_not_change_state():
    state = {"player": {"coins": 3}}
    assert (
        apply_fantasy_setup({"fantasy_mechanics": {"profile": "unknown"}}, state, {})
        is state
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("energy_max", 0),
        ("energy_max", True),
        ("initial_energy", 101),
        ("bounty_reward", -1),
        ("rest_cost", 4),
        ("corpse_item_id", "missing"),
    ],
)
def test_invalid_configuration_is_rejected(key, value):
    data = snapshot()
    data["fantasy_mechanics"][key] = value
    with pytest.raises(InvalidSchemaInitialError):
        apply_fantasy_setup(data, {}, {"outlander_class": CLASSES[0]})


def test_null_energy_keeps_energy_unset():
    data = snapshot()
    data["fantasy_mechanics"]["energy_max"] = None
    data["fantasy_mechanics"]["initial_energy"] = None
    result = apply_fantasy_setup(data, {}, {"outlander_class": CLASSES[0]})
    assert "energy" not in result["player"]
