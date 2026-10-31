from app.engine.overtures.succession_hook import remove_ruler, remove_ruler_change
from app.engine.succession.heirs import regent_id_for
from app.models.world_diplomacy import TruceState
from app.models.world_state import WorldState
from strategy_contracts.peace import PeaceTier

from tests.engine.succession.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    leader_of,
    make_succession_world,
)


def _world_with_player_treaty() -> WorldState:
    world = make_succession_world()
    low, high = sorted((PLAYER, WRATHFUL_RIVAL))
    world.truces.append(
        TruceState(
            id="truce_1",
            faction_a=low,
            faction_b=high,
            expires_turn=world.clock.turn + 50,
            signed_turn=world.clock.turn,
            tier=PeaceTier.GENERATION,
            signatory_leader_ids=[
                world.factions[low].leader_id,
                world.factions[high].leader_id,
            ],
        )
    )
    return world


def test_ruleset_one_removal_installs_a_regent_not_a_copy_of_the_ruler() -> None:
    world = make_succession_world()
    old = leader_of(world, WRATHFUL_RIVAL)

    remove_ruler(world, SCENARIO, WRATHFUL_RIVAL)

    assert old.is_alive is False
    assert world.factions[WRATHFUL_RIVAL].leader_id == regent_id_for(WRATHFUL_RIVAL)


def test_ruleset_one_removal_still_queues_renewals_with_the_player() -> None:
    world = _world_with_player_treaty()

    remove_ruler(world, SCENARIO, WRATHFUL_RIVAL)

    assert world.overture_renewals == ["truce_1"]


def test_removal_reports_the_leader_id_change_for_the_event_log() -> None:
    world = make_succession_world()
    before = world.factions[WRATHFUL_RIVAL].leader_id

    changes = remove_ruler_change(world, SCENARIO, WRATHFUL_RIVAL)

    assert [change.path for change in changes] == [
        f"factions.{WRATHFUL_RIVAL}.leader_id"
    ]
    assert changes[0].before == before
    assert changes[0].after == regent_id_for(WRATHFUL_RIVAL)


def test_removing_an_already_dead_ruler_changes_nothing() -> None:
    world = make_succession_world()
    leader_of(world, WRATHFUL_RIVAL).is_alive = False

    assert remove_ruler(world, SCENARIO, WRATHFUL_RIVAL) == []
    assert world.succession.crises == []


def test_ruleset_one_player_ruler_cannot_be_removed() -> None:
    world = make_succession_world()
    before = world.factions[PLAYER].leader_id

    assert remove_ruler(world, SCENARIO, PLAYER) == []
    assert world.factions[PLAYER].leader_id == before
    assert world.succession.crises == []
