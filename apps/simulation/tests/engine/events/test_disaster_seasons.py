from app.engine.hashing import world_hash
from tests.engine.events.builders import (
    always_event,
    make_disaster_world,
    make_scenario,
    npc_events,
    pending_ids,
    run_events,
)
from tests.engine.events.test_events_phase import _run as run_legacy_events
from tests.engine.events.test_events_phase import _world as legacy_world

LEGACY_EVENTS_HASH = "86542754bdc5da9ddbf75b7baa1bf2cac67fd2a0670a2cbc94b1f858e7cfcf59"
HARVEST_FIRST_MONTH = 8
HARVEST_LAST_MONTH = 10
MONTHS_IN_YEAR = 12
LEGACY_TIER_ONE_UNREST = 40


def test_bad_harvest_fires_only_in_harvest_months() -> None:
    for month in range(1, MONTHS_IN_YEAR + 1):
        after, _ = run_events(make_disaster_world(month), make_scenario())

        is_harvest = HARVEST_FIRST_MONTH <= month <= HARVEST_LAST_MONTH
        assert ("bad_harvest" in pending_ids(after)) is is_harvest, month


def test_the_season_follows_the_clock_across_turns() -> None:
    fired = []
    for turn in range(4):
        world = make_disaster_world(month=7)
        world.clock.turn = turn
        after, _ = run_events(world, make_scenario())
        fired.append("bad_harvest" in pending_ids(after))

    assert fired == [False, True, False, False]


def test_ruleset_one_world_has_no_disaster_templates_and_no_npc_firing() -> None:
    world = make_disaster_world()
    world.events_ruleset = 1
    scenario = make_scenario(
        chance=None, extra_events=(always_event("always_npc", applies=True),)
    )

    after, events = run_events(world, scenario)

    assert "bad_harvest" not in pending_ids(after)
    assert npc_events(events) == []


def test_chance_zero_never_fires_for_anyone() -> None:
    after, events = run_events(make_disaster_world(), make_scenario(chance=0))

    assert "bad_harvest" not in pending_ids(after)
    assert npc_events(events) == []


def test_ruleset_one_events_hash_is_unchanged_by_the_new_gate() -> None:
    after, _ = run_legacy_events(legacy_world(unrest=LEGACY_TIER_ONE_UNREST))

    assert world_hash(after) == LEGACY_EVENTS_HASH
