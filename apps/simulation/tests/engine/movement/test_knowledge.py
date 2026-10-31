import itertools

import pytest
from app.engine.movement.knowledge import known_hazards, visible_regions
from app.engine.movement.map_index import build_map_index
from app.models.world_diplomacy import EnvoyState
from strategy_contracts.enums import RelationStatus, Terrain

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    FACTION_C,
    make_army,
    make_map,
    make_world_for,
)

NAMES = ["reg_a", "reg_b", "reg_c", "reg_d", "reg_e", "reg_f"]
INDEX = build_map_index(
    make_map({name: Terrain.PLAIN for name in NAMES}, list(itertools.pairwise(NAMES)))
)
AB = (FACTION_A, FACTION_B)
AC = (FACTION_A, FACTION_C)
BC = (FACTION_B, FACTION_C)


def _owners(**by_region: str | None) -> dict[str, str | None]:
    owners: dict[str, str | None] = dict.fromkeys(NAMES)
    owners.update(by_region)
    return owners


def _visible(owners, armies=(), statuses=None, faction=FACTION_A):
    world = make_world_for(owners, list(armies), statuses)
    return visible_regions(world, faction, INDEX)


def _hazards(owners, armies=(), statuses=None, faction=FACTION_A):
    world = make_world_for(owners, list(armies), statuses)
    return known_hazards(world, faction, INDEX)


def test_a_faction_sees_its_own_regions_and_their_neighbours() -> None:
    assert _visible(_owners(reg_c=FACTION_A)) == {"reg_b", "reg_c", "reg_d"}


def test_a_faction_sees_wherever_its_armies_stand() -> None:
    army = make_army("army_a", FACTION_A, "reg_e")
    assert _visible(_owners(reg_a=FACTION_A), [army]) == {"reg_a", "reg_b", "reg_e"}


def test_an_army_does_not_reveal_its_neighbours() -> None:
    army = make_army("army_a", FACTION_A, "reg_e")
    assert "reg_d" not in _visible(_owners(), [army])
    assert "reg_f" not in _visible(_owners(), [army])


def test_a_rival_armies_and_regions_do_not_widen_my_view() -> None:
    owners = _owners(reg_a=FACTION_A, reg_e=FACTION_B)
    army = make_army("army_b", FACTION_B, "reg_f")
    assert _visible(owners, [army]) == {"reg_a", "reg_b"}


def test_allies_share_what_they_see() -> None:
    owners = _owners(reg_a=FACTION_A, reg_e=FACTION_B)
    army = make_army("army_b", FACTION_B, "reg_c")
    visible = _visible(owners, [army], {AB: RelationStatus.ALLIANCE})
    assert visible == {"reg_a", "reg_b", "reg_c", "reg_d", "reg_e", "reg_f"}


def test_vision_is_not_shared_with_friends_of_my_ally() -> None:
    owners = _owners(reg_a=FACTION_A, reg_f=FACTION_C)
    statuses = {AB: RelationStatus.ALLIANCE, BC: RelationStatus.ALLIANCE}
    assert "reg_f" not in _visible(owners, statuses=statuses)


def test_envoy_reveals_host_capital_only() -> None:
    world = make_world_for(_owners(reg_f=FACTION_B))
    world.factions[FACTION_B].capital_region_id = "reg_f"
    world.envoys = [
        EnvoyState(id="envoy_a", from_faction_id=FACTION_A, at_faction_id=FACTION_B)
    ]

    assert "reg_f" in visible_regions(world, FACTION_A, INDEX)


@pytest.mark.parametrize("status", [RelationStatus.PEACE, RelationStatus.WAR, None])
def test_a_visible_region_owned_by_another_faction_is_a_hazard(
    status: RelationStatus | None,
) -> None:
    statuses = {AB: status} if status else {}
    assert _hazards(_owners(reg_a=FACTION_A, reg_b=FACTION_B), statuses=statuses) == {
        "reg_b"
    }


def test_a_region_owned_by_an_ally_is_not_a_hazard() -> None:
    owners = _owners(reg_a=FACTION_A, reg_b=FACTION_B)
    assert _hazards(owners, statuses={AB: RelationStatus.ALLIANCE}) == set()


def test_my_own_regions_are_never_hazards() -> None:
    assert _hazards(_owners(reg_a=FACTION_A, reg_b=FACTION_A)) == set()


def test_unowned_regions_are_not_hazards() -> None:
    assert _hazards(_owners(reg_a=FACTION_A)) == set()


def test_a_visible_foreign_army_makes_its_region_a_hazard() -> None:
    army = make_army("army_b", FACTION_B, "reg_b")
    assert _hazards(_owners(reg_a=FACTION_A), [army]) == {"reg_b"}


def test_a_foreign_army_in_my_own_region_is_a_hazard() -> None:
    army = make_army("army_b", FACTION_B, "reg_a")
    assert _hazards(_owners(reg_a=FACTION_A), [army]) == {"reg_a"}


def test_an_allied_army_is_not_a_hazard() -> None:
    army = make_army("army_b", FACTION_B, "reg_b")
    owners = _owners(reg_a=FACTION_A)
    assert _hazards(owners, [army], {AB: RelationStatus.ALLIANCE}) == set()


def test_my_own_army_is_not_a_hazard() -> None:
    army = make_army("army_a2", FACTION_A, "reg_b")
    assert _hazards(_owners(reg_a=FACTION_A), [army]) == set()


def test_fogged_foreign_land_is_not_assumed_to_be_a_hazard() -> None:
    owners = _owners(reg_a=FACTION_A, reg_e=FACTION_B, reg_f=FACTION_B)
    army = make_army("army_b", FACTION_B, "reg_d")
    assert _hazards(owners, [army]) == set()


def test_a_fogged_enemy_army_is_not_known() -> None:
    army = make_army("army_b", FACTION_B, "reg_f")
    assert _hazards(_owners(reg_a=FACTION_A), [army]) == set()


def test_hazards_are_always_a_subset_of_what_is_visible() -> None:
    owners = _owners(reg_a=FACTION_A, reg_b=FACTION_B, reg_e=FACTION_C)
    armies = [make_army("army_c", FACTION_C, "reg_c")]
    world = make_world_for(owners, armies)
    assert known_hazards(world, FACTION_A, INDEX) <= visible_regions(
        world, FACTION_A, INDEX
    )


def test_a_destroyed_or_unknown_faction_sees_nothing() -> None:
    world = make_world_for(_owners(reg_a=FACTION_A))
    assert visible_regions(world, "house_nobody", INDEX) == frozenset()
