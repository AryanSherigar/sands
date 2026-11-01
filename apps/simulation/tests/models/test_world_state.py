from app.models.world_state import WORLD_SCHEMA_VERSION, WorldState

from tests.models.builders import make_world


def test_world_round_trips_through_json() -> None:
    world = make_world()
    assert WorldState.model_validate_json(world.model_dump_json()) == world


def test_new_world_carries_the_current_schema_version() -> None:
    assert make_world().schema_version == WORLD_SCHEMA_VERSION


def test_schema_version_is_six_after_visibility_ruleset() -> None:
    assert WORLD_SCHEMA_VERSION == 6
