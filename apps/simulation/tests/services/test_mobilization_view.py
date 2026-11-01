from app.models.world_diplomacy import OutrageState
from app.services.world_projection import project_world
from strategy_contracts.scene import OutrageLevel
from tests.engine.outrage.builders import PLAYER, SCENARIO, WRATHFUL_RIVAL, make_world

TURNS_LEFT = 3


def _mobilize(world, faction_id: str) -> None:
    world.outrage.append(
        OutrageState(
            faction_id=faction_id,
            level=OutrageLevel.NONE,
            expires_turn=0,
            mobilized_until_turn=world.clock.turn + TURNS_LEFT,
        )
    )


def test_the_player_sees_how_long_their_own_mobilization_lasts() -> None:
    world = make_world()
    _mobilize(world, PLAYER)

    view = project_world(world, SCENARIO, 1, "digest")

    assert view.mobilization is not None
    assert view.mobilization.turns_left == TURNS_LEFT


def test_no_mobilization_view_when_not_mobilized() -> None:
    assert project_world(make_world(), SCENARIO, 1, "digest").mobilization is None


def test_a_rivals_mobilization_never_appears_in_the_view() -> None:
    world = make_world()
    _mobilize(world, WRATHFUL_RIVAL)

    view = project_world(world, SCENARIO, 1, "digest")

    assert view.mobilization is None
