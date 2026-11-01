import pytest
from app.models.world_diplomacy import WarState
from app.models.world_region import OccupationState
from app.models.world_siege import SiegeState
from pydantic import ValidationError

from tests.engine.diplomacy.builders import make_world


def test_new_world_enables_the_siege_ruleset() -> None:
    world = make_world()

    assert world.siege_ruleset == 1
    assert world.sieges == []


def test_legacy_siege_ruleset_omits_siege_fields_from_the_document() -> None:
    world = make_world()
    world.siege_ruleset = 0

    document = world.model_dump(mode="json")

    assert "siege_ruleset" not in document
    assert "sieges" not in document


def test_current_siege_ruleset_keeps_siege_fields_in_the_document() -> None:
    document = make_world().model_dump(mode="json")

    assert document["siege_ruleset"] == 1
    assert document["sieges"] == []


def test_war_state_omits_empty_siege_scoring_fields() -> None:
    war = WarState(
        id="war_1", attacker_id="house_a", defender_id="house_b", started_turn=0
    )

    document = war.model_dump(mode="json")

    assert "scored_region_ids" not in document
    assert "occupation_points_attacker" not in document
    assert "occupation_points_defender" not in document


def test_war_state_keeps_siege_scoring_fields_once_used() -> None:
    war = WarState(
        id="war_1",
        attacker_id="house_a",
        defender_id="house_b",
        started_turn=0,
        scored_region_ids=["region_1"],
        occupation_points_attacker=20,
    )

    document = war.model_dump(mode="json")

    assert document["scored_region_ids"] == ["region_1"]
    assert document["occupation_points_attacker"] == 20


def test_occupation_state_defaults_hold_turns_to_zero() -> None:
    occupation = OccupationState(occupier_id="house_a", siege_progress=100)

    assert occupation.hold_turns == 0


def test_siege_state_rejects_negative_progress() -> None:
    with pytest.raises(ValidationError):
        SiegeState(
            region_id="r", besieger_id="house_a", army_ids=["army_1"], progress=-1
        )
