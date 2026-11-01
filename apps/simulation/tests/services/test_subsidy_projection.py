from app.models.world_pressure import SubsidyState
from app.services.pressure_projection import project_subsidies
from app.services.world_projection import project_world
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

SUBSIDY_KEYS = {
    "id",
    "payer_id",
    "receiver_id",
    "war_id",
    "amount_per_turn",
    "turns_left",
}


def _world_with_subsidies():
    world = make_world()
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    for identifier, payer, receiver, expires in (
        ("subsidy_2", CAUTIOUS_RIVAL, PLAYER, world.clock.turn + 3),
        ("subsidy_1", PLAYER, WRATHFUL_RIVAL, world.clock.turn),
        ("subsidy_3", CAUTIOUS_RIVAL, WRATHFUL_RIVAL, world.clock.turn + 1),
    ):
        world.pressure.subsidies.append(
            SubsidyState(
                id=identifier,
                payer_id=payer,
                receiver_id=receiver,
                war_id="war_1",
                expires_turn=expires,
                amount_per_turn=7,
            )
        )
    return world


def test_player_sees_subsidies_they_pay_or_receive() -> None:
    world = _world_with_subsidies()

    views = project_subsidies(world, PLAYER)

    assert [view.id for view in views] == ["subsidy_1", "subsidy_2"]
    assert [view.turns_left for view in views] == [1, 4]
    assert set(views[0].model_dump()) == SUBSIDY_KEYS


def test_unrelated_subsidies_are_hidden() -> None:
    world = _world_with_subsidies()

    assert [view.id for view in project_subsidies(world, WRATHFUL_RIVAL)] == [
        "subsidy_1",
        "subsidy_3",
    ]
    assert project_subsidies(make_world(), PLAYER) == []


def test_the_world_view_carries_only_the_players_subsidies() -> None:
    world = _world_with_subsidies()

    view = project_world(world, SCENARIO, 1, "digest")

    assert [item.id for item in view.subsidies] == ["subsidy_1", "subsidy_2"]
