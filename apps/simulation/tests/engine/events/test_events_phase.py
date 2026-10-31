from app.engine.events.constants import MAX_NEW_EVENTS_PER_TURN
from app.engine.events.phase import EventsPhase
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.models.world_army import ArmyState
from app.models.world_character import GovernorState
from app.models.world_event_memory import EventMemory
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.conditions import ConditionScope
from strategy_contracts.enums import TroopType
from strategy_contracts.examples import load_three_crowns
from tests.models.builders import make_region, make_world

PLAYER = "house_carrow"
HOME = "carrow_vale"
GOVERNOR = "gov_carrow"
TURN = 5
TIER_ONE_UNREST = 40
TIER_TWO_UNREST = 60
TIER_THREE_UNREST = 90
TIER_TWO_OPINION = -30
SCARRED_POINTS = 30
EXTRA_REGION_COUNT = 5
FULL_FREQUENCY = 100


def _world(unrest: int = 10, opinion: int = 0) -> WorldState:
    world = make_world()
    world.events_ruleset = 1
    world.clock.turn = TURN
    world.regions[HOME].unrest = unrest
    world.regions[HOME].governor_id = GOVERNOR
    world.governors[GOVERNOR] = GovernorState(
        id=GOVERNOR, name="Lord Harl", region_id=HOME, opinion_of_ruler=opinion
    )
    return world


def _context(frequency: int = FULL_FREQUENCY) -> PhaseContext:
    scenario = load_three_crowns()
    scenario.tuning.event_frequency_percent = frequency
    return PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(42, TURN, "events"),
        resolved_outcomes={},
        recorded_answers={},
    )


def _run(world: WorldState, frequency: int = FULL_FREQUENCY):
    result = EventsPhase().run(world, _context(frequency))
    return result.world, result.events


def _grievance_tiers(world: WorldState) -> list[int]:
    return [
        pending.tier
        for pending in world.pending_events
        if pending.template_id == "tax_grievance"
    ]


def test_phase_is_inert_without_the_events_ruleset() -> None:
    world = _world(unrest=TIER_THREE_UNREST)
    world.events_ruleset = 0
    after, events = _run(world)
    assert after.pending_events == []
    assert events == []


def test_unrest_fires_a_grievance_about_that_region() -> None:
    after, events = _run(_world(unrest=TIER_ONE_UNREST))
    (pending,) = after.pending_events
    assert pending.template_id == "tax_grievance"
    assert pending.subject_kind is ConditionScope.REGION
    assert pending.subject_id == HOME
    assert pending.tier == 1
    assert pending.created_turn == TURN
    assert pending.deadline_turn == TURN + 1
    assert pending.cause_inputs["region_unrest"] == TIER_ONE_UNREST
    assert pending.choice_ids == ["ease_taxes", "garrison_crackdown"]
    assert [event.kind for event in events] == ["event_fired"]
    assert after.counters[CounterKind.PENDING_EVENT] == 1


def test_below_the_first_tier_nothing_fires() -> None:
    after, _ = _run(_world(unrest=TIER_ONE_UNREST - 1))
    assert after.pending_events == []


def test_a_pending_event_blocks_a_duplicate() -> None:
    world, _ = _run(_world(unrest=TIER_ONE_UNREST))
    again, _ = _run(world)
    assert len(again.pending_events) == 1


def test_same_tier_does_not_refire_once_answered() -> None:
    world, _ = _run(_world(unrest=TIER_ONE_UNREST))
    world.pending_events.clear()
    again, _ = _run(world)
    assert again.pending_events == []


def test_higher_tier_refires_only_when_its_whole_trigger_holds() -> None:
    world, _ = _run(_world(unrest=TIER_ONE_UNREST))
    world.pending_events.clear()
    world.regions[HOME].unrest = TIER_TWO_UNREST
    still_tier_one, _ = _run(world)
    assert still_tier_one.pending_events == []
    world.governors[GOVERNOR].opinion_of_ruler = TIER_TWO_OPINION
    escalated, _ = _run(world)
    assert _grievance_tiers(escalated) == [2]


def test_a_scar_makes_trouble_arrive_a_tier_sooner() -> None:
    world = _world(unrest=TIER_ONE_UNREST)
    world.event_memories.append(
        EventMemory(template_id="tax_grievance", subject_id=HOME, scar=SCARRED_POINTS)
    )
    after, _ = _run(world)
    assert [pending.tier for pending in after.pending_events] == [2]


def test_governor_without_a_region_governor_cannot_hold_the_opinion_tier() -> None:
    world = _world(unrest=TIER_TWO_UNREST, opinion=TIER_TWO_OPINION)
    world.regions[HOME].governor_id = None
    after, _ = _run(world)
    assert _grievance_tiers(after) == [1]


def test_governor_opinion_fires_a_defiance_about_that_governor() -> None:
    after, _ = _run(_world(opinion=TIER_TWO_OPINION))
    (pending,) = after.pending_events
    assert pending.template_id == "noble_defiance"
    assert pending.subject_kind is ConditionScope.GOVERNOR
    assert pending.subject_name == "Lord Harl"


def test_unpaid_army_fires_a_mutiny_about_that_army() -> None:
    world = _world()
    world.armies["army_p"] = ArmyState(
        id="army_p",
        owner_id=PLAYER,
        troops={TroopType.INFANTRY: 50},
        morale=50,
        location_id=HOME,
        unpaid_turns=1,
    )
    after, _ = _run(world)
    (pending,) = after.pending_events
    assert pending.template_id == "unpaid_mutiny"
    assert pending.subject_kind is ConditionScope.ARMY
    assert pending.subject_id == "army_p"
    assert pending.cause_inputs == {"army_unpaid_turns": 1, "army_morale": 50}


def test_several_restless_regions_raise_the_faction_wide_event() -> None:
    world = _world(unrest=TIER_TWO_UNREST)
    world.regions["east_march"] = make_region("east_march", PLAYER)
    world.regions["east_march"].unrest = TIER_TWO_UNREST
    after, _ = _run(world)
    kinds = {pending.subject_kind for pending in after.pending_events}
    assert ConditionScope.FACTION in kinds
    turmoil = next(
        p for p in after.pending_events if p.template_id == "realm_in_turmoil"
    )
    assert turmoil.subject_id == PLAYER
    assert turmoil.cause_inputs["regions_with_unrest_at_least"] == 2


def test_new_events_per_turn_are_capped_worst_first() -> None:
    world = _world()
    for index in range(EXTRA_REGION_COUNT):
        region_id = f"march_{index}"
        world.regions[region_id] = make_region(region_id, PLAYER)
        world.regions[region_id].unrest = TIER_THREE_UNREST
    after, _ = _run(world)
    assert len(after.pending_events) == MAX_NEW_EVENTS_PER_TURN
    assert all(pending.tier == 3 for pending in after.pending_events)
    ids = [
        p.subject_id for p in after.pending_events if p.template_id == "tax_grievance"
    ]
    assert ids == sorted(ids)


def test_zero_frequency_never_fires() -> None:
    after, _ = _run(_world(unrest=TIER_THREE_UNREST), frequency=0)
    assert after.pending_events == []


def test_events_are_deterministic() -> None:
    first, _ = _run(_world(unrest=TIER_THREE_UNREST), frequency=50)
    second, _ = _run(_world(unrest=TIER_THREE_UNREST), frequency=50)
    assert first.pending_events == second.pending_events


def test_other_factions_regions_are_not_subjects() -> None:
    world = _world()
    world.regions["ashford"].unrest = TIER_THREE_UNREST
    after, _ = _run(world)
    assert after.pending_events == []
