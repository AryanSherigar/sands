from app.engine.movement.engagement import open_or_join_battle
from app.models.world_battle import BattleSide, BattleState
from app.models.world_state import WorldState

from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    make_world,
)


def _spare_army(world: WorldState, owner_id: str, identity: str, region_id: str) -> str:
    template = next(army for army in world.armies.values() if army.owner_id == owner_id)
    clone = template.model_copy(
        update={"id": identity, "location_id": region_id}, deep=True
    )
    world.armies[identity] = clone
    return identity


def _world_with_open_battle() -> tuple[WorldState, str, list[str]]:
    world = make_world()
    region_id = next(iter(world.regions))
    first = _spare_army(world, PLAYER, "army_p1", region_id)
    second = _spare_army(world, CAUTIOUS_RIVAL, "army_c1", region_id)
    open_or_join_battle(world, region_id, [first], [second])
    third = _spare_army(world, PLAYER, "army_p2", region_id)
    fourth = _spare_army(world, CAUTIOUS_RIVAL, "army_c2", region_id)
    return world, region_id, [third, fourth]


def test_reinforcements_with_reversed_labels_join_their_factions_existing_side() -> (
    None
):
    world, region_id, (player_army, rival_army) = _world_with_open_battle()

    battle = open_or_join_battle(world, region_id, [rival_army], [player_army])

    assert battle.attacker_army_ids == ["army_p1", "army_p2"]
    assert battle.defender_army_ids == ["army_c1", "army_c2"]
    assert battle.contingents[PLAYER].side is BattleSide.ATTACKER
    assert battle.contingents[CAUTIOUS_RIVAL].side is BattleSide.DEFENDER


def test_the_joined_battle_is_a_valid_battle_state() -> None:
    world, region_id, (player_army, rival_army) = _world_with_open_battle()

    battle = open_or_join_battle(world, region_id, [rival_army], [player_army])

    BattleState.model_validate(battle.model_dump())


def test_reinforcements_with_matching_labels_are_unchanged() -> None:
    world, region_id, (player_army, rival_army) = _world_with_open_battle()

    battle = open_or_join_battle(world, region_id, [player_army], [rival_army])

    assert battle.attacker_army_ids == ["army_p1", "army_p2"]
    assert battle.defender_army_ids == ["army_c1", "army_c2"]
