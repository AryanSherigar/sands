from app.models.world_army import MarchState
from strategy_contracts.enums import PayLevel, TroopType

from tests.engine.economy.builders import (
    ELSEWHERE,
    HOME,
    PLAYER,
    RIVAL,
    TEST_TUNING,
    events_of,
    make_army,
    make_faction,
    make_region,
    make_scenario,
    make_world,
    run_economy,
)

TUNING = TEST_TUNING


def _paid_world(army, treasury: int = 500):
    return make_world(
        regions=[make_region(HOME, PLAYER), make_region(ELSEWHERE, RIVAL)],
        factions=[make_faction(PLAYER, treasury=treasury), make_faction(RIVAL)],
        armies=[army],
    )


def _broke_world(*armies):
    """A rival-less faction with no income and an empty treasury."""
    return make_world(
        factions=[make_faction(PLAYER, treasury=0)],
        armies=list(armies),
    )


def test_a_paid_army_resting_at_home_recovers_morale() -> None:
    result = run_economy(_paid_world(make_army("army_x", PLAYER, morale=50)))
    assert result.world.armies["army_x"].morale == 55
    [event] = events_of(result, "army_rested")
    assert event.cause.inputs["morale_gain"] == 5


def test_reduced_pay_recovers_less_morale() -> None:
    army = make_army("army_x", PLAYER, morale=50, pay_level=PayLevel.REDUCED)
    assert run_economy(_paid_world(army)).world.armies["army_x"].morale == 52


def test_morale_recovery_stops_at_one_hundred() -> None:
    army = make_army("army_x", PLAYER, morale=98)
    assert run_economy(_paid_world(army)).world.armies["army_x"].morale == 100


def test_an_army_away_from_home_does_not_recover() -> None:
    army = make_army("army_x", PLAYER, location_id=ELSEWHERE, morale=50)
    assert run_economy(_paid_world(army)).world.armies["army_x"].morale == 50


def test_a_marching_army_does_not_recover() -> None:
    march = MarchState(from_id=HOME, to_id=ELSEWHERE)
    army = make_army("army_x", PLAYER, morale=50, march=march)
    assert run_economy(_paid_world(army)).world.armies["army_x"].morale == 50


def test_paying_resets_the_unpaid_streak() -> None:
    army = make_army("army_x", PLAYER, unpaid_turns=1)
    assert run_economy(_paid_world(army)).world.armies["army_x"].unpaid_turns == 0


def test_an_unpaid_army_loses_morale_and_the_faction_defaults() -> None:
    result = run_economy(_broke_world(make_army("army_x", PLAYER, morale=50)))
    army = result.world.armies["army_x"]
    faction = result.world.factions[PLAYER]
    assert (army.morale, army.unpaid_turns) == (42, 1)
    assert (faction.credit_strikes, faction.reputation) == (1, -5)
    [event] = events_of(result, "army_unpaid")
    assert event.cause.inputs == {"unpaid_turns": 1, "morale_loss": 8}


def test_a_default_is_logged_once_however_many_armies_go_unpaid() -> None:
    armies = [make_army("army_x", PLAYER), make_army("army_y", PLAYER)]
    result = run_economy(_broke_world(*armies))
    assert len(events_of(result, "faction_defaulted")) == 1
    assert result.world.factions[PLAYER].credit_strikes == 1


def test_morale_never_drops_below_zero() -> None:
    result = run_economy(_broke_world(make_army("army_x", PLAYER, morale=3)))
    assert result.world.armies["army_x"].morale == 0


def test_troops_desert_once_the_streak_reaches_the_threshold() -> None:
    army = make_army("army_x", PLAYER, unpaid_turns=1)
    result = run_economy(_broke_world(army))
    [event] = events_of(result, "army_deserted")
    assert result.world.armies["army_x"].troops == {TroopType.INFANTRY: 180}
    assert event.cause.inputs == {"lost_infantry": 20}


def test_a_first_unpaid_turn_does_not_cause_desertion() -> None:
    result = run_economy(_broke_world(make_army("army_x", PLAYER)))
    assert events_of(result, "army_deserted") == []


def test_desertion_is_per_troop_type_and_rounds_up() -> None:
    troops = {TroopType.INFANTRY: 15, TroopType.CAVALRY: 5}
    army = make_army("army_x", PLAYER, troops=troops, unpaid_turns=1)
    result = run_economy(_broke_world(army))
    assert result.world.armies["army_x"].troops == {
        TroopType.INFANTRY: 13,
        TroopType.CAVALRY: 4,
    }


def test_an_army_that_deserts_to_nothing_is_dissolved() -> None:
    troops = {TroopType.INFANTRY: 1}
    army = make_army("army_x", PLAYER, troops=troops, unpaid_turns=1)
    result = run_economy(_broke_world(army))
    assert "army_x" not in result.world.armies
    assert len(events_of(result, "army_dissolved")) == 1


def test_desertion_threshold_is_tunable() -> None:
    scenario = make_scenario(desertion_after_unpaid_turns=1)
    result = run_economy(_broke_world(make_army("army_x", PLAYER)), scenario)
    assert result.world.armies["army_x"].troops == {TroopType.INFANTRY: 180}


def test_with_money_for_only_some_armies_the_lower_ids_are_paid_first() -> None:
    world = make_world(
        factions=[make_faction(PLAYER, treasury=30)],
        armies=[make_army("army_b", PLAYER), make_army("army_a", PLAYER)],
    )
    declared = run_economy(world).world
    assert declared.armies["army_a"].unpaid_turns == 0
    assert declared.armies["army_b"].unpaid_turns == 1
