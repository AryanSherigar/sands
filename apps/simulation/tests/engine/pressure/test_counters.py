from app.engine.pressure.counters import (
    add_humiliation,
    raise_devastation,
    update_stalemate,
)

from tests.engine.pressure.builders import PLAYER, SCENARIO, add_war, make_world

TUNING = SCENARIO.tuning.pressure


def test_new_war_starts_at_zero_then_stalemate_grows_while_scores_are_unchanged() -> (
    None
):
    world = make_world()
    war = add_war(world)

    update_stalemate(world, {war.id: (0, 0)})
    assert world.pressure.stalemate_turns[war.id] == 0
    update_stalemate(world, {war.id: (0, 0)})
    update_stalemate(world, {war.id: (0, 0)})

    assert world.pressure.stalemate_turns[war.id] == 2


def test_stalemate_counter_resets_on_score_change() -> None:
    world = make_world()
    war = add_war(world)
    world.pressure.stalemate_turns[war.id] = 5
    war.war_score_attacker = 10

    update_stalemate(world, {war.id: (0, 0)})

    assert world.pressure.stalemate_turns[war.id] == 0


def test_finished_wars_drop_their_counters() -> None:
    world = make_world()
    world.pressure.stalemate_turns["war_gone"] = 4

    update_stalemate(world, {})

    assert "war_gone" not in world.pressure.stalemate_turns


def test_humiliation_is_capped() -> None:
    world = make_world()

    add_humiliation(world, SCENARIO, PLAYER, TUNING.humiliation_cap + 50)
    add_humiliation(world, SCENARIO, PLAYER, 10)

    assert world.pressure.humiliation[PLAYER] == TUNING.humiliation_cap


def test_devastation_rises_by_step_and_caps_at_one_hundred() -> None:
    world = make_world()
    region_id = next(r.id for r in world.regions.values() if r.owner_id == PLAYER)

    raise_devastation(world, SCENARIO, region_id)
    assert world.pressure.devastation[region_id] == TUNING.devastation_step
    for _ in range(20):
        raise_devastation(world, SCENARIO, region_id)

    assert world.pressure.devastation[region_id] == 100
