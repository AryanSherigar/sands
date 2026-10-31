from app.engine.events.constants import MAX_NEW_EVENTS_PER_TURN
from app.engine.events.decay import decay_memories
from app.engine.events.memory import find_memory
from app.engine.hashing import world_hash
from app.models.world_state import WorldState
from tests.engine.events.builders import (
    NPC,
    PLAYER,
    always_event,
    make_disaster_world,
    make_scenario,
    npc_events,
    pending_ids,
    run_events,
)

PLAGUE_MONTH = 7
HARVEST_MONTH = 9
OFF_SEASON_MONTH = 1
PLAGUE_EXHAUSTION = 30
HIGH_TREASURY = 1000
EMPTY_TREASURY = 0
BUY_GRAIN_COST = 80
FIRST_STRIKE_TIER = 1
SCARRED_TIER = 2
NEGLECT_SCAR = 30


def _plague_world(treasury: int) -> WorldState:
    world = make_disaster_world(PLAGUE_MONTH)
    world.factions[NPC].war_exhaustion = PLAGUE_EXHAUSTION
    world.factions[NPC].treasury = treasury
    return world


def test_opted_in_template_resolves_for_an_npc_without_a_prompt() -> None:
    after, events = run_events(make_disaster_world(), make_scenario())

    (resolved,) = [
        event for event in npc_events(events) if event.cause.subject_ids == [NPC]
    ]
    assert resolved.cause.summary_key.startswith("events.bad_harvest.")
    assert resolved.cause.inputs["tier"] == FIRST_STRIKE_TIER
    assert all(pending.subject_id != NPC for pending in after.pending_events)


def test_template_without_the_flag_never_fires_for_npcs() -> None:
    scenario = make_scenario(
        chance=0, extra_events=(always_event("quiet_event", applies=False),)
    )

    after, events = run_events(make_disaster_world(OFF_SEASON_MONTH), scenario)

    assert npc_events(events) == []
    assert "quiet_event" in pending_ids(after)


def test_npc_takes_the_first_choice_when_it_can_afford_it() -> None:
    world = make_disaster_world()
    world.factions[NPC].treasury = HIGH_TREASURY

    after, events = run_events(world, make_scenario())

    (resolved,) = npc_events(events)
    assert resolved.cause.summary_key == "events.bad_harvest.buy_grain"
    assert after.factions[NPC].treasury == HIGH_TREASURY - BUY_GRAIN_COST


def test_npc_takes_the_neglect_effects_when_it_cannot_afford_the_first_choice() -> None:
    after, events = run_events(_plague_world(EMPTY_TREASURY), make_scenario())

    resolved = [
        event
        for event in npc_events(events)
        if event.cause.summary_key.startswith("events.plague.")
    ]
    assert [event.cause.summary_key for event in resolved] == [
        "events.plague.neglected"
    ]
    assert after.factions[NPC].treasury == EMPTY_TREASURY


def test_destroyed_and_leaderless_npcs_never_fire() -> None:
    destroyed = make_disaster_world()
    destroyed.factions[NPC].is_destroyed = True
    leaderless = make_disaster_world()
    leaderless.factions[NPC].leader_id = None

    assert npc_events(run_events(destroyed, make_scenario())[1]) == []
    assert npc_events(run_events(leaderless, make_scenario())[1]) == []


def test_npc_scar_escalates_a_repeat_strike_and_decays() -> None:
    world = make_disaster_world()
    world.factions[NPC].treasury = EMPTY_TREASURY
    scenario = make_scenario()

    world, _ = run_events(world, scenario)
    memory = find_memory(world, "bad_harvest", NPC)
    assert memory is not None
    assert (memory.last_tier, memory.scar) == (FIRST_STRIKE_TIER, NEGLECT_SCAR)

    world, events = run_events(world, scenario)
    assert find_memory(world, "bad_harvest", NPC).last_tier == SCARRED_TIER
    assert any(
        event.cause.inputs["tier"] == SCARRED_TIER for event in npc_events(events)
    )

    decay_memories(world, scenario, PLAYER)
    assert find_memory(world, "bad_harvest", NPC).scar < NEGLECT_SCAR * 2


def test_npc_memory_decay_reads_the_npcs_own_conditions() -> None:
    world = _plague_world(HIGH_TREASURY)
    scenario = make_scenario()
    world, _ = run_events(world, scenario)
    memory = find_memory(world, "plague", NPC)
    assert memory is not None and memory.last_tier == FIRST_STRIKE_TIER

    for _ in range(scenario.events[1].tier_calm_turns + 1):
        decay_memories(world, scenario, PLAYER)

    memory = find_memory(world, "plague", NPC)
    assert memory is not None
    assert memory.last_tier == FIRST_STRIKE_TIER and memory.calm_turns == 0


def test_npc_firing_is_capped_per_faction() -> None:
    extras = tuple(always_event(f"always_{index}", applies=True) for index in range(5))
    scenario = make_scenario(chance=0, extra_events=extras)

    _, events = run_events(make_disaster_world(OFF_SEASON_MONTH), scenario)

    assert len(npc_events(events)) == MAX_NEW_EVENTS_PER_TURN


def test_player_events_still_create_pending_prompts() -> None:
    after, events = run_events(make_disaster_world(), make_scenario())

    assert "bad_harvest" in pending_ids(after)
    assert all(event.cause.subject_ids != [PLAYER] for event in npc_events(events))


def test_same_seed_gives_the_same_npc_outcomes() -> None:
    first, first_events = run_events(make_disaster_world(), make_scenario())
    second, second_events = run_events(make_disaster_world(), make_scenario())

    assert world_hash(first) == world_hash(second)
    assert first_events == second_events
