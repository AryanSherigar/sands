from app.models.orders import MergeArmiesOrder, SplitArmyOrder
from strategy_contracts.enums import TroopType

from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    RIVAL,
    events_of,
    make_army,
    make_faction,
    make_region,
    make_world,
    queued,
    run_economy,
)


def _world(*armies):
    return make_world(
        regions=[make_region(HOME, PLAYER, wealth=100, manpower=80)],
        factions=[make_faction(PLAYER, treasury=500), make_faction(RIVAL)],
        armies=list(armies),
    )


def _rejection(result) -> str:
    [event] = events_of(result, "economy_order_rejected")
    return event.cause.summary_key


def test_merge_pools_troops_into_the_target_and_removes_the_rest() -> None:
    first = make_army("army_a", PLAYER, troops={TroopType.INFANTRY: 100})
    second = make_army(
        "army_b", PLAYER, troops={TroopType.INFANTRY: 50, TroopType.CAVALRY: 20}
    )
    order = queued(
        MergeArmiesOrder(
            faction_id=PLAYER, army_ids=["army_a", "army_b"], into_army_id="army_a"
        )
    )

    result = run_economy(_world(first, second), orders=[order])

    assert set(result.world.armies) == {"army_a"}
    assert result.world.armies["army_a"].troops == {
        TroopType.INFANTRY: 150,
        TroopType.CAVALRY: 20,
    }
    assert len(events_of(result, "armies_merged")) == 1


def test_merge_refuses_armies_in_different_places() -> None:
    first = make_army("army_a", PLAYER)
    second = make_army("army_b", PLAYER, location_id="elsewhere")
    order = queued(
        MergeArmiesOrder(
            faction_id=PLAYER, army_ids=["army_a", "army_b"], into_army_id="army_a"
        )
    )

    result = run_economy(_world(first, second), orders=[order])

    assert _rejection(result) == "economy_order_rejected_different_location"
    assert set(result.world.armies) == {"army_a", "army_b"}


def test_merge_target_must_be_one_of_the_armies() -> None:
    first = make_army("army_a", PLAYER)
    second = make_army("army_b", PLAYER)
    order = queued(
        MergeArmiesOrder(
            faction_id=PLAYER, army_ids=["army_a", "army_b"], into_army_id="army_c"
        )
    )

    assert (
        _rejection(run_economy(_world(first, second), orders=[order]))
        == "economy_order_rejected_invalid_merge"
    )


def test_split_moves_the_chosen_troops_to_a_new_army_in_the_same_place() -> None:
    army = make_army(
        "army_a", PLAYER, troops={TroopType.INFANTRY: 100, TroopType.CAVALRY: 30}
    )
    order = queued(
        SplitArmyOrder(
            faction_id=PLAYER, army_id="army_a", troops={TroopType.CAVALRY: 30}
        )
    )

    result = run_economy(_world(army), orders=[order])

    [child_id] = [army_id for army_id in result.world.armies if army_id != "army_a"]
    assert result.world.armies["army_a"].troops == {TroopType.INFANTRY: 100}
    child = result.world.armies[child_id]
    assert child.troops == {TroopType.CAVALRY: 30}
    assert child.location_id == result.world.armies["army_a"].location_id
    assert len(events_of(result, "army_split")) == 1


def test_split_cannot_take_everything_or_more_than_exists() -> None:
    army = make_army("army_a", PLAYER, troops={TroopType.INFANTRY: 100})
    everything = queued(
        SplitArmyOrder(
            faction_id=PLAYER, army_id="army_a", troops={TroopType.INFANTRY: 100}
        )
    )
    too_many = queued(
        SplitArmyOrder(
            faction_id=PLAYER, army_id="army_a", troops={TroopType.INFANTRY: 500}
        )
    )

    assert (
        _rejection(run_economy(_world(army), orders=[everything]))
        == "economy_order_rejected_invalid_split"
    )
    assert (
        _rejection(run_economy(_world(army), orders=[too_many]))
        == "economy_order_rejected_invalid_split"
    )
