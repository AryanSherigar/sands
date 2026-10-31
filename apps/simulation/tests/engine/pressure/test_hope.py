from app.engine.pressure.hope import derive_hope
from app.engine.pressure.shocks import record_shock
from app.models.world_pressure import MediationOffer, SubsidyState
from app.models.world_region import ImprovementState, OccupationState
from strategy_contracts.enums import ImprovementKind
from strategy_contracts.pressure import HopeSource, ShockKind

from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.pressure


def _quiet_world():
    world = make_world()
    war = add_war(world)
    for army in world.armies.values():
        if army.owner_id == PLAYER:
            army.morale = 0
    return world, war


def test_no_sources_means_no_hope() -> None:
    world, war = _quiet_world()

    reading = derive_hope(world, SCENARIO, PLAYER, war)

    assert (reading.sources, reading.reasons, reading.bonus) == ([], [], 0)


def test_subsidy_and_mediation_provide_hope_until_expiry() -> None:
    world, war = _quiet_world()
    world.pressure.subsidies.append(
        SubsidyState(
            id="sub_1",
            payer_id=CAUTIOUS_RIVAL,
            receiver_id=PLAYER,
            war_id=war.id,
            expires_turn=2,
        )
    )
    world.pressure.mediation_offers.append(
        MediationOffer(
            id="med_1", mediator_id=CAUTIOUS_RIVAL, war_id=war.id, expires_turn=2
        )
    )

    live = derive_hope(world, SCENARIO, PLAYER, war)
    world.clock.turn = 3
    expired = derive_hope(world, SCENARIO, PLAYER, war)

    assert set(live.sources) == {HopeSource.SUBSIDY, HopeSource.MEDIATION}
    assert expired.sources == []


def test_hope_lists_each_source_with_reason() -> None:
    world, war = _quiet_world()
    world.pressure.subsidies.append(
        SubsidyState(
            id="sub_1",
            payer_id=CAUTIOUS_RIVAL,
            receiver_id=PLAYER,
            war_id=war.id,
            expires_turn=9,
        )
    )

    reading = derive_hope(world, SCENARIO, PLAYER, war)

    assert reading.reasons == ["subsidy:sub_1"]
    assert reading.bonus == TUNING.hope_will_bonus


def test_relief_army_counts_only_if_unbeaten() -> None:
    world, war = _quiet_world()
    army = next(a for a in world.armies.values() if a.owner_id == PLAYER)

    beaten = derive_hope(world, SCENARIO, PLAYER, war)
    army.morale = TUNING.relief_army_min_morale
    steady = derive_hope(world, SCENARIO, PLAYER, war)

    assert HopeSource.RELIEF_ARMY not in beaten.sources
    assert HopeSource.RELIEF_ARMY in steady.sources


def test_held_fortress_counts_only_while_unoccupied() -> None:
    world, war = _quiet_world()
    region = next(r for r in world.regions.values() if r.owner_id == PLAYER)
    region.improvements = [
        ImprovementState(kind=ImprovementKind.FORT, turns_remaining=0)
    ]

    held = derive_hope(world, SCENARIO, PLAYER, war)
    region.occupation = OccupationState(occupier_id=WRATHFUL_RIVAL, siege_progress=100)
    lost = derive_hope(world, SCENARIO, PLAYER, war)

    assert HopeSource.HELD_FORTRESS in held.sources
    assert HopeSource.HELD_FORTRESS not in lost.sources


def test_new_enemy_shock_cancels_all_hope_then_it_returns() -> None:
    world, war = _quiet_world()
    world.pressure.subsidies.append(
        SubsidyState(
            id="sub_1",
            payer_id=CAUTIOUS_RIVAL,
            receiver_id=PLAYER,
            war_id=war.id,
            expires_turn=99,
        )
    )
    record_shock(world, SCENARIO, ShockKind.NEW_ENEMY, PLAYER, war.id)

    cancelled = derive_hope(world, SCENARIO, PLAYER, war)
    world.clock.turn = TUNING.hope_cancel_turns + 1
    returned = derive_hope(world, SCENARIO, PLAYER, war)

    assert cancelled.sources == []
    assert HopeSource.SUBSIDY in returned.sources


def test_alliance_source_returns_no_hope() -> None:
    world, war = _quiet_world()

    assert (
        HopeSource.ALLIED_ARMY not in derive_hope(world, SCENARIO, PLAYER, war).sources
    )
