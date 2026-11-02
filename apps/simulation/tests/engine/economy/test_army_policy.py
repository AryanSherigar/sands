from app.engine.battle_records import populate_battle_contingents
from app.models.orders import SetArmyPolicyOrder
from app.models.world_battle import BattleState
from strategy_contracts.battle import ReservePolicy, WithdrawalPolicy

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


def test_a_preset_is_stored_on_the_army() -> None:
    order = queued(
        SetArmyPolicyOrder(
            faction_id=PLAYER,
            army_id="army_a",
            withdrawal_policy=WithdrawalPolicy.PRESERVE,
            reserve_policy=ReservePolicy.REINFORCE_ON_PRESSURE,
        )
    )

    result = run_economy(_world(make_army("army_a", PLAYER)), orders=[order])

    army = result.world.armies["army_a"]
    assert army.withdrawal_policy is WithdrawalPolicy.PRESERVE
    assert army.reserve_policy is ReservePolicy.REINFORCE_ON_PRESSURE


def test_an_unset_army_serializes_exactly_as_before() -> None:
    document = make_army("army_a", PLAYER).model_dump(mode="json")
    assert "withdrawal_policy" not in document
    assert "reserve_policy" not in document


def test_another_factions_army_is_refused() -> None:
    order = queued(
        SetArmyPolicyOrder(
            faction_id=PLAYER,
            army_id="army_r",
            withdrawal_policy=WithdrawalPolicy.PRESERVE,
        )
    )

    result = run_economy(_world(make_army("army_r", RIVAL)), orders=[order])

    assert len(events_of(result, "economy_order_rejected")) == 1
    assert result.world.armies["army_r"].withdrawal_policy is None


def test_a_new_battle_starts_from_the_armys_presets() -> None:
    world = _world(
        make_army(
            "army_a",
            PLAYER,
            withdrawal_policy=WithdrawalPolicy.PRESERVE,
            reserve_policy=ReservePolicy.REINFORCE_ON_PRESSURE,
        ),
        make_army("army_r", RIVAL),
    )
    battle = BattleState(
        id="battle_1",
        region_id=HOME,
        attacker_army_ids=["army_a"],
        defender_army_ids=["army_r"],
    )

    populate_battle_contingents(world, battle)

    assert (
        battle.contingents[PLAYER].plan.withdrawal_policy is WithdrawalPolicy.PRESERVE
    )
    assert (
        battle.contingents[PLAYER].plan.reserve_policy
        is ReservePolicy.REINFORCE_ON_PRESSURE
    )
    assert battle.contingents[RIVAL].plan.withdrawal_policy is WithdrawalPolicy.BALANCED
