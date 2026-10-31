from app.engine.ai.generators.alliance import denounce_candidates
from app.models.orders import DenounceAllianceOrder
from app.models.world_ai import AimState
from app.models.world_diplomacy import GroundState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.stances import ScoreCategory

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    make_world,
)

TUNING = SCENARIO.tuning.ai
STRENGTH = 80


def _world(target: str = WRATHFUL_RIVAL, has_ground: bool = True):
    world = make_world()
    world.grounds = []
    alliance = add_alliance(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)
    world.aims[CAUTIOUS_RIVAL] = AimState(
        category=ScoreCategory.ATTACK,
        target_faction_id=target,
        chosen_turn=0,
        leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
        capital_held=True,
    )
    if has_ground:
        world.grounds.append(
            GroundState(
                id="ground_1",
                kind=GroundKind.CLAIM,
                holder_faction_id=CAUTIOUS_RIVAL,
                holder_leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
                target_faction_id=WRATHFUL_RIVAL,
                region_id=next(
                    key
                    for key, region in sorted(world.regions.items())
                    if region.owner_id == WRATHFUL_RIVAL
                ),
                strength=STRENGTH,
                since_turn=0,
                is_personal=False,
            )
        )
    return world, alliance


def _denounce(world, scenario=SCENARIO):
    return denounce_candidates(world, scenario, CAUTIOUS_RIVAL)


def test_an_ally_that_is_the_aim_target_with_a_ground_is_denounced() -> None:
    world, alliance = _world()
    candidates = _denounce(world)
    assert [item.order for item in candidates] == [
        DenounceAllianceOrder(faction_id=CAUTIOUS_RIVAL, alliance_id=alliance.id)
    ]
    assert candidates[0].category is ScoreCategory.ATTACK
    assert candidates[0].base_score == TUNING.denounce_bonus


def test_an_ally_that_is_not_the_aim_target_is_kept() -> None:
    world, _ = _world(target=PLAYER)
    assert _denounce(world) == []


def test_no_ground_means_no_denunciation() -> None:
    world, _ = _world(has_ground=False)
    assert _denounce(world) == []


def test_no_aim_means_no_denunciation() -> None:
    world, _ = _world()
    world.aims.clear()
    assert _denounce(world) == []


def test_the_alliance_toggle_disables_the_generator() -> None:
    world, _ = _world()
    scenario = SCENARIO.model_copy(deep=True)
    scenario.toggles.is_ai_alliance_enabled = False
    assert _denounce(world, scenario) == []
