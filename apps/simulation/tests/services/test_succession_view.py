from app.models.world_character import LeaderState
from app.models.world_succession import CrisisState
from app.services.world_projection import project_world
from strategy_contracts.succession import HealthBand, HeirSetup
from tests.engine.succession.builders import (
    PLAYER,
    SCENARIO,
    leader_of,
    make_succession_world,
    make_world,
)

VERSION = 1
DIGEST = "digest"


def _view(world, scenario=SCENARIO):
    return project_world(world, scenario, VERSION, DIGEST)


def test_ruleset_zero_world_has_no_succession_view() -> None:
    world = make_world()
    world.succession_ruleset = 0

    view = _view(world)

    assert view.succession is None


def test_succession_view_projects_ruler_health_and_heir() -> None:
    scenario = SCENARIO.model_copy(deep=True)
    heir = HeirSetup(id="heir_1", name="Prince Colin", age=18, trait_ids=["cautious"])
    scenario.leaders[0].heir = heir

    world = make_succession_world()
    leader = leader_of(world, PLAYER)
    leader.age = 45

    view = _view(world, scenario)

    assert view.succession is not None
    assert view.succession.ruler_health is not None
    assert view.succession.ruler_health.age == 45
    assert view.succession.ruler_health.health_band is HealthBand.ROBUST
    assert view.succession.heir is not None
    assert view.succession.heir.name == "Prince Colin"
    assert view.succession.heir.is_minor is False
    assert view.succession.crisis is None


def test_succession_view_flags_minor_heir() -> None:
    scenario = SCENARIO.model_copy(deep=True)
    heir = HeirSetup(id="heir_1", name="Young Colin", age=12)
    scenario.leaders[0].heir = heir

    world = make_succession_world()
    view = _view(world, scenario)

    assert view.succession is not None
    assert view.succession.heir is not None
    assert view.succession.heir.is_minor is True


def test_succession_view_projects_active_crisis() -> None:
    world = make_succession_world()
    world.leaders["regent_player"] = LeaderState(
        id="regent_player",
        name="Regent Morwen",
        faction_id=PLAYER,
        trait_ids=["pragmatic"],
        age=45,
    )
    world.succession.crises.append(
        CrisisState(
            faction_id=PLAYER,
            ends_turn=8,
            regent_id="regent_player",
        )
    )

    view = _view(world)

    assert view.succession is not None
    assert view.succession.crisis is not None
    assert view.succession.crisis.is_active is True
    assert view.succession.crisis.regent_name == "Regent Morwen"
    assert view.succession.crisis.ends_turn == 8
