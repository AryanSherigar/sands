from app.engine.ending_rules.hegemony import is_hegemon, is_hegemonic_position
from app.engine.ending_rules.streaks import advance_ending_streaks

from tests.engine.ending_rules.builders import PLAYER, make_world, scenario_with


def _grab_all_regions(world) -> None:
    for region in world.regions.values():
        region.owner_id = PLAYER


def test_default_start_is_not_hegemonic() -> None:
    assert not is_hegemonic_position(make_world(), scenario_with())


def test_hegemony_by_regions_after_streak() -> None:
    scenario = scenario_with(hegemony_streak_turns=2, hegemony_wealth_percent=100)
    world = make_world()
    _grab_all_regions(world)
    advance_ending_streaks(world, scenario)
    assert not is_hegemon(world, scenario)
    advance_ending_streaks(world, scenario)
    assert is_hegemon(world, scenario)


def test_hegemony_by_wealth_after_streak() -> None:
    scenario = scenario_with(
        hegemony_streak_turns=1, hegemony_region_percent=100, hegemony_wealth_percent=60
    )
    world = make_world()
    for faction_id, faction in world.factions.items():
        faction.treasury = 1000 if faction_id == PLAYER else 0
    advance_ending_streaks(world, scenario)
    assert is_hegemon(world, scenario)


def test_negative_treasuries_count_as_zero_wealth() -> None:
    scenario = scenario_with(hegemony_region_percent=100)
    world = make_world()
    for faction in world.factions.values():
        faction.treasury = -500
    assert not is_hegemonic_position(world, scenario)


def _hoard_all_gold(world) -> None:
    for faction_id, faction in world.factions.items():
        faction.treasury = 1000 if faction_id == PLAYER else 0


def test_wealth_alone_is_not_hegemony_without_enough_land() -> None:
    scenario = scenario_with(
        hegemony_region_percent=100,
        hegemony_wealth_percent=60,
        hegemony_wealth_min_region_percent=100,
    )
    world = make_world()
    _hoard_all_gold(world)

    assert not is_hegemonic_position(world, scenario)


def test_a_collapsing_realm_is_not_hegemon_by_wealth_or_land() -> None:
    scenario = scenario_with(
        hegemony_region_percent=100,
        hegemony_wealth_percent=60,
        hegemony_wealth_min_region_percent=0,
        hegemony_min_stability=50,
    )
    world = make_world()
    _hoard_all_gold(world)
    assert is_hegemonic_position(world, scenario)

    world.factions[PLAYER].stability = 10
    assert not is_hegemonic_position(world, scenario)
    _grab_all_regions(world)
    assert not is_hegemonic_position(world, scenario)
