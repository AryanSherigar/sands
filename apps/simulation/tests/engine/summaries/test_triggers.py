from app.engine.summaries.triggers import evaluate_summary_triggers
from app.models.world_events import EventCause, EventLogEntry, PhaseName
from tests.engine.battles.builders import ATTACKER, DEFENDER, battle_fixture


def _event(
    seq: int,
    subjects: list[str],
    *,
    major: bool = False,
    significance: int = 0,
) -> EventLogEntry:
    return EventLogEntry(
        seq=seq,
        turn=0,
        phase=PhaseName.INTERNAL,
        kind=f"event_{seq}",
        is_major=major,
        significance=significance,
        cause=EventCause(summary_key=f"event_{seq}", subject_ids=subjects),
    )


def test_threshold_request_contains_only_player_known_events_and_is_idempotent() -> (
    None
):
    world, scenario = battle_fixture()
    world.summary_ruleset = 1
    scenario.tuning.summary_significance_threshold = 5
    events = [
        _event(1, [DEFENDER], major=True, significance=10),
        _event(2, [ATTACKER], significance=5),
    ]

    request = evaluate_summary_triggers(world, scenario, events)

    assert request is not None
    assert request.trigger == "significance"
    assert request.event_seqs == [2]
    assert world.summary_event_cursor == 2
    assert world.significance.points == 0
    assert evaluate_summary_triggers(world, scenario, events) is None
    assert len(world.summary_requests) == 1


def test_visible_major_event_triggers_a_single_coalesced_request() -> None:
    world, scenario = battle_fixture()
    world.summary_ruleset = 1
    events = [
        _event(4, [ATTACKER], significance=3),
        _event(5, ["uprising_field_0", ATTACKER, "field"], major=True),
    ]

    request = evaluate_summary_triggers(world, scenario, events)

    assert request is not None
    assert request.trigger == "major_event"
    assert request.event_seqs == [4, 5]
    assert request.id == "summary:4:5"


def test_corrected_rules_retain_threshold_contributors_across_batches() -> None:
    world, scenario = battle_fixture()
    world.summary_ruleset = 2
    scenario.tuning.summary_significance_threshold = 5
    first = _event(1, [ATTACKER], significance=3)
    first.kind = "faction_war_pressure_changed"
    second = _event(2, [ATTACKER], significance=2)
    second.kind = "faction_war_pressure_changed"
    assert evaluate_summary_triggers(world, scenario, [first]) is None
    request = evaluate_summary_triggers(world, scenario, [second])
    assert request.event_seqs == [1, 2]
    assert len(request.facts) == 2


def test_corrected_rules_deny_mixed_subjects_and_unknown_event_kinds() -> None:
    world, scenario = battle_fixture()
    world.summary_ruleset = 2
    assert (
        evaluate_summary_triggers(
            world,
            scenario,
            [
                _event(1, [ATTACKER, DEFENDER], major=True),
            ],
        )
        is None
    )
    assert world.summary_requests == []


def test_corrected_battle_outcome_is_observed_only_by_participant() -> None:
    from tests.engine.battles.builders import start_battle

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    world.summary_ruleset = 2
    event = _event(1, [world.battles[0].id], major=True)
    event.kind = "battle_exchange_resolved"
    request = evaluate_summary_triggers(world, scenario, [event])
    assert request is not None
    assert request.facts[0].kind == "battle_exchange_resolved"
    assert request.facts[0].region_ids == ["field"]


def test_existing_v1_request_serialization_has_no_new_fact_fields() -> None:
    world, scenario = battle_fixture()
    world.summary_ruleset = 1
    evaluate_summary_triggers(world, scenario, [_event(1, [ATTACKER], major=True)])
    document = world.model_dump(mode="json")
    assert "summary_pending_facts" not in document
    assert "facts" not in document["summary_requests"][0]


def test_new_rules_batch_reordering_and_retries_are_deterministic() -> None:
    from app.engine.hashing import world_hash

    first, scenario = battle_fixture()
    first.summary_ruleset = 2
    second = first.model_copy(deep=True)
    a = _event(1, [ATTACKER], significance=5)
    a.kind = "faction_war_pressure_changed"
    b = _event(2, [ATTACKER], major=True)
    b.kind = "faction_war_pressure_changed"
    evaluate_summary_triggers(first, scenario, [b, a, a])
    evaluate_summary_triggers(second, scenario, [a, b])
    assert world_hash(first) == world_hash(second)
    assert evaluate_summary_triggers(first, scenario, [a, b]) is None
