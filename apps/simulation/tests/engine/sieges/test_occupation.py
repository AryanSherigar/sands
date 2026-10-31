from app.engine.sieges.occupation import hold_occupations
from app.models.world_diplomacy import RelationStatus

from tests.engine.sieges.builders import (
    BESIEGER,
    BESIEGER_ARMY,
    SCENARIO,
    TARGET_OWNER,
    TARGET_REGION,
    make_siege_world,
    occupy,
)

HOLD_DELAY = SCENARIO.tuning.siege.hold_delay


def test_hold_counts_up_then_transfers_ownership() -> None:
    world = make_siege_world()
    occupy(world)
    region = world.regions[TARGET_REGION]
    unrest_before = region.unrest

    for expected in range(1, HOLD_DELAY):
        hold_occupations(world, SCENARIO)
        assert region.occupation is not None
        assert region.occupation.hold_turns == expected
        assert region.owner_id == TARGET_OWNER
    events = hold_occupations(world, SCENARIO)

    assert region.owner_id == BESIEGER
    assert region.occupation is None
    assert TARGET_OWNER in region.claimant_ids
    assert region.unrest == min(100, unrest_before + 20)
    assert [event.kind for event in events] == ["region_conquered"]
    assert events[0].is_major


def test_transfer_records_a_conquest() -> None:
    world = make_siege_world()
    occupy(world, hold_turns=HOLD_DELAY - 1)

    hold_occupations(world, SCENARIO)

    assert [item.faction_id for item in world.coalition.conquests] == [BESIEGER]


def test_occupation_lifted_when_the_occupier_army_is_gone() -> None:
    world = make_siege_world()
    occupy(world)
    world.armies[BESIEGER_ARMY].location_id = "ashford"

    events = hold_occupations(world, SCENARIO)

    assert world.regions[TARGET_REGION].occupation is None
    assert world.regions[TARGET_REGION].owner_id == TARGET_OWNER
    assert [event.kind for event in events] == ["occupation_lifted"]


def test_occupation_lifted_when_the_war_has_ended() -> None:
    world = make_siege_world()
    occupy(world)
    for relation in world.relations:
        relation.status = RelationStatus.PEACE

    events = hold_occupations(world, SCENARIO)

    assert world.regions[TARGET_REGION].occupation is None
    assert [event.kind for event in events] == ["occupation_lifted"]


def test_conquest_unrest_is_clamped_at_one_hundred() -> None:
    world = make_siege_world()
    occupy(world, hold_turns=HOLD_DELAY - 1)
    world.regions[TARGET_REGION].unrest = 95

    hold_occupations(world, SCENARIO)

    assert world.regions[TARGET_REGION].unrest == 100


def test_owner_destroyed_mid_hold_still_transfers() -> None:
    world = make_siege_world()
    occupy(world, hold_turns=HOLD_DELAY - 1)
    world.factions[TARGET_OWNER].is_destroyed = True
    world.factions[TARGET_OWNER].leader_id = None

    hold_occupations(world, SCENARIO)

    assert world.regions[TARGET_REGION].owner_id == BESIEGER
