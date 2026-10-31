from app.engine.ai.situation import is_hostile, war_enemies
from app.models.world_diplomacy import RelationState, WarState
from strategy_contracts.enums import RelationStatus

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    WRATHFUL_RIVAL,
    make_world,
)


def test_peaceful_world_has_no_enemies() -> None:
    assert war_enemies(make_world(), CAUTIOUS_RIVAL) == []


def test_war_state_makes_enemies_on_both_sides() -> None:
    world = make_world()
    world.wars.append(
        WarState(
            id="war_1",
            attacker_id=WRATHFUL_RIVAL,
            defender_id=CAUTIOUS_RIVAL,
            started_turn=0,
        )
    )

    assert war_enemies(world, CAUTIOUS_RIVAL) == [WRATHFUL_RIVAL]
    assert war_enemies(world, WRATHFUL_RIVAL) == [CAUTIOUS_RIVAL]


def test_war_relation_counts_without_a_war_record() -> None:
    world = make_world()
    low, high = sorted((CAUTIOUS_RIVAL, PLAYER))
    world.relations = [
        RelationState(
            faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=0
        )
    ]

    assert war_enemies(world, CAUTIOUS_RIVAL) == [PLAYER]
    assert is_hostile(world, PLAYER)
