from app.engine.pressure.shocks import record_shock
from app.engine.pressure.will import compute_will
from app.models.world_diplomacy import DiplomaticPlayState
from app.models.world_pressure import SubsidyState
from strategy_contracts.pressure import ShockKind
from strategy_contracts.terms import CedeRegionTerm

from tests.engine.diplomacy.builders import set_traits
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.pressure


def _war_world(traits: list[str] | None = None):
    world = make_world()
    war = add_war(world)
    set_traits(world, PLAYER, traits or ["pragmatic"])
    return world, war


def _set_morale(world, value: int) -> None:
    for army in world.armies.values():
        if army.owner_id == PLAYER:
            army.morale = value


def test_peace_faction_has_no_will_pressure() -> None:
    reading = compute_will(make_world(), SCENARIO, PLAYER)

    assert (reading.value, reading.floor, reading.factors) == (0, 0, {})


def test_will_follows_average_army_morale() -> None:
    world, _ = _war_world()
    _set_morale(world, 20)
    low = compute_will(world, SCENARIO, PLAYER)
    _set_morale(world, 100)
    high = compute_will(world, SCENARIO, PLAYER)

    assert high.factors["morale"] > low.factors["morale"]
    assert high.value > low.value


def test_pride_and_aggression_raise_floor_caution_lowers_it() -> None:
    proud, _ = _war_world(["proud"])
    wrathful, _ = _war_world(["wrathful"])
    cautious, _ = _war_world(["cautious"])

    floors = {
        name: compute_will(world, SCENARIO, PLAYER).floor
        for name, world in (
            ("proud", proud),
            ("wrathful", wrathful),
            ("cautious", cautious),
        )
    }

    assert floors["proud"] > floors["cautious"]
    assert floors["wrathful"] > floors["cautious"]


def test_shocks_subtract_once_from_value_and_floor() -> None:
    world, war = _war_world(["proud"])
    _set_morale(world, 100)
    before = compute_will(world, SCENARIO, PLAYER)

    record_shock(world, SCENARIO, ShockKind.CAPITAL_FALLS, PLAYER, war.id)
    record_shock(world, SCENARIO, ShockKind.CAPITAL_FALLS, PLAYER, war.id)
    after = compute_will(world, SCENARIO, PLAYER)

    assert after.factors["shocks"] == -TUNING.shock_amounts[ShockKind.CAPITAL_FALLS]
    assert after.value < before.value
    assert after.floor < before.floor


def test_hope_adds_bonus_and_new_enemy_removes_it() -> None:
    world, war = _war_world()
    world.pressure.subsidies.append(
        SubsidyState(
            id="sub_1",
            payer_id=CAUTIOUS_RIVAL,
            receiver_id=PLAYER,
            war_id=war.id,
            expires_turn=99,
        )
    )
    _set_morale(world, 0)
    hopeful = compute_will(world, SCENARIO, PLAYER)
    record_shock(world, SCENARIO, ShockKind.NEW_ENEMY, PLAYER, war.id)
    cancelled = compute_will(world, SCENARIO, PLAYER)

    assert hopeful.factors["hope"] == TUNING.hope_will_bonus
    assert cancelled.factors["hope"] == 0


def test_extinction_demand_raises_floor() -> None:
    world, _ = _war_world()
    baseline = compute_will(world, SCENARIO, PLAYER).floor
    capital_id = world.factions[PLAYER].capital_region_id
    world.plays.append(
        DiplomaticPlayState(
            id="play_1",
            attacker_id=WRATHFUL_RIVAL,
            defender_id=PLAYER,
            demands=[
                CedeRegionTerm(
                    from_faction_id=PLAYER,
                    to_faction_id=WRATHFUL_RIVAL,
                    region_id=capital_id,
                )
            ],
            stage="demand",
        )
    )

    assert (
        compute_will(world, SCENARIO, PLAYER).floor
        == baseline + TUNING.extinction_floor
    )


def test_low_stability_with_hostile_governors_shifts_toward_peace_party() -> None:
    world, _ = _war_world()
    world.factions[PLAYER].stability = 80
    steady = compute_will(world, SCENARIO, PLAYER).factors["party"]
    world.factions[PLAYER].stability = 20
    for governor in world.governors.values():
        if world.regions[governor.region_id].owner_id == PLAYER:
            governor.opinion_of_ruler = -60

    assert compute_will(world, SCENARIO, PLAYER).factors["party"] < steady


def test_invasion_unity_when_enemy_army_on_home_soil() -> None:
    world, _ = _war_world()
    baseline = compute_will(world, SCENARIO, PLAYER).factors["invasion_unity"]
    home = next(r for r in world.regions.values() if r.owner_id == PLAYER)
    raider = next(a for a in world.armies.values() if a.owner_id == WRATHFUL_RIVAL)
    raider.location_id = home.id

    assert compute_will(world, SCENARIO, PLAYER).factors["invasion_unity"] > baseline


def test_humiliation_and_plunder_raise_will() -> None:
    world, war = _war_world()
    baseline = compute_will(world, SCENARIO, PLAYER)
    world.pressure.humiliation[PLAYER] = 20
    war.war_score_defender = 60

    reading = compute_will(world, SCENARIO, PLAYER)

    assert reading.factors["humiliation"] > baseline.factors["humiliation"]
    assert reading.factors["plunder"] > baseline.factors["plunder"]


def test_value_never_below_floor() -> None:
    world, war = _war_world(["proud"])
    _set_morale(world, 0)
    world.factions[PLAYER].stability = 0
    for kind in ShockKind:
        record_shock(world, SCENARIO, kind, PLAYER, war.id)

    reading = compute_will(world, SCENARIO, PLAYER)

    assert reading.value >= reading.floor
