from app.engine.revolt.arming import arm_revolt_talk
from app.engine.revolt.closing import close_revolt_talk
from app.services.covenant_projection import project_covenants
from strategy_contracts.revolt import CovenantKind
from strategy_contracts.scene import ChoiceOutcome
from tests.engine.revolt.test_revolt_talk import PLAYER, _negotiate, _scenario, _world


def test_the_player_sees_the_covenants_they_gave() -> None:
    scenario = _scenario()
    world = _negotiate(_world(), scenario).world
    arm_revolt_talk(world, scenario)
    closed, _ = close_revolt_talk(
        world,
        scenario,
        world.progress.pending_scene_id,
        ChoiceOutcome(option_id="charter"),
    )
    views = project_covenants(closed, PLAYER)
    assert {view.covenant for view in views} == {
        CovenantKind.TAX_RELIEF,
        CovenantKind.GARRISON_OUT,
    }
    assert project_covenants(closed, "someone_else") == []
