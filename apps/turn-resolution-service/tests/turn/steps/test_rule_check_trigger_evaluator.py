"""Rising-edge triggering, queueing and stamping of rule checks."""

from app.turn.steps.rule_check_trigger_evaluator import (
    evaluate_rule_check_triggers,
)

NOW_MS = 1_760_000_000_000


def _check(check_id: str, trigger: dict, priority: int = 0, **overrides) -> dict:
    base = {
        "check_id": check_id,
        "label": f"check {check_id}",
        "kind": "timed_choice",
        "trigger_condition_expression": trigger,
        "priority": priority,
        "result_path": "rules.r3",
        "params": {
            "prompt": f"Prompt {check_id}",
            "options": [
                {
                    "id": "answer",
                    "label": "Answer",
                    "result": "answered",
                    "mutations": [],
                },
                {
                    "id": "ignore",
                    "label": "Ignore",
                    "result": "ignored",
                    "mutations": [],
                },
            ],
            "window_ms": 12000,
            "timeout_result": "ignored",
        },
        "narrator_instruction_template": None,
    }
    base.update(overrides)
    return base


def _snapshot(*checks: dict, tools: list[str] | None = None) -> dict:
    return {
        "enabled_tools": ["rule_checks"] if tools is None else tools,
        "rule_checks": list(checks),
    }


def _run(snapshot: dict, state: dict, **overrides):
    options = {"participant_count": 1, "can_open": True, "now_ms": NOW_MS}
    options.update(overrides)
    return evaluate_rule_check_triggers(snapshot, state, **options)


CLOCK_PAST_5 = {"field": "clock", "op": ">=", "value": 5}
FLAG_SET = {"field": "alarm", "op": "==", "value": True}


def test_rising_edge_opens_the_check_and_stamps_pending_state() -> None:
    state = {"clock": 6}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state)

    pending = state["_pending_check"]
    assert pending["kind"] == "timed_choice"
    assert pending["check_def_id"] == "a"
    assert pending["issued_at"] == NOW_MS
    assert pending["window_ms"] == 12000
    assert pending["prompt"] == "Prompt a"
    assert pending["options"] == [
        {"id": "answer", "label": "Answer"},
        {"id": "ignore", "label": "Ignore"},
    ]
    assert result.payload.check_id == pending["check_id"]
    assert {"_pending_check", "_check_edges"} <= result.mutated_paths


def test_pending_state_and_payload_never_carry_results_or_mutations() -> None:
    state = {"clock": 6}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state)

    dumped = str(state["_pending_check"]) + result.payload.model_dump_json()
    for secret in ("answered", "ignored", "timeout_result", "mutations", "result"):
        assert secret not in dumped


def test_trigger_that_stays_true_fires_once() -> None:
    check = _check("a", CLOCK_PAST_5)
    state = {"clock": 6}
    _run(_snapshot(check), state)
    state.pop("_pending_check")

    second = _run(_snapshot(check), state)

    assert second.payload is None
    assert "_pending_check" not in state


def test_flag_set_reset_set_fires_twice() -> None:
    check = _check("a", FLAG_SET)
    snapshot = _snapshot(check)
    state = {"alarm": True}
    first = _run(snapshot, state)
    state.pop("_pending_check")
    state["alarm"] = False
    reset = _run(snapshot, state)
    state["alarm"] = True
    second = _run(snapshot, state)

    assert first.payload is not None
    assert reset.payload is None
    assert second.payload is not None


def test_simultaneous_triggers_queue_in_priority_order() -> None:
    late = _check("late", CLOCK_PAST_5, priority=5)
    early = _check("early", CLOCK_PAST_5, priority=1)
    state = {"clock": 6}

    result = _run(_snapshot(late, early), state)

    assert result.payload.prompt == "Prompt early"
    assert state["_check_queue"] == ["late"]


def test_queued_check_opens_on_a_later_turn_when_nothing_blocks() -> None:
    snapshot = _snapshot(
        _check("early", CLOCK_PAST_5, priority=1),
        _check("late", CLOCK_PAST_5, priority=5),
    )
    state = {"clock": 6}
    _run(snapshot, state)
    state.pop("_pending_check")

    second = _run(snapshot, state)

    assert second.payload.prompt == "Prompt late"
    assert state["_check_queue"] == []


def test_blocked_turn_queues_without_opening() -> None:
    state = {"clock": 6}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state, can_open=False)

    assert result.payload is None
    assert "_pending_check" not in state
    assert state["_check_queue"] == ["a"]


def test_an_already_pending_check_blocks_opening() -> None:
    state = {"clock": 6, "_pending_check": {"check_id": "old"}}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state)

    assert result.payload is None
    assert state["_pending_check"] == {"check_id": "old"}
    assert state["_check_queue"] == ["a"]


def test_a_pending_minigame_blocks_opening() -> None:
    state = {"clock": 6, "_pending_minigame": {"minigame_id": "m"}}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state)

    assert result.payload is None
    assert state["_check_queue"] == ["a"]


def test_queue_does_not_duplicate_a_waiting_check() -> None:
    check = _check("a", FLAG_SET)
    snapshot = _snapshot(check)
    state = {"alarm": True}
    _run(snapshot, state, can_open=False)
    state["alarm"] = False
    _run(snapshot, state, can_open=False)
    state["alarm"] = True

    _run(snapshot, state, can_open=False)

    assert state["_check_queue"] == ["a"]


def test_queue_overflow_is_dropped() -> None:
    checks = [_check(f"c{i}", CLOCK_PAST_5, priority=i) for i in range(10)]
    state = {"clock": 6}

    _run(_snapshot(*checks), state, can_open=False)

    assert state["_check_queue"] == [f"c{i}" for i in range(8)]


def test_tool_off_does_nothing() -> None:
    state = {"clock": 6}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5), tools=[]), state)

    assert result.payload is None
    assert result.mutated_paths == set()
    assert state == {"clock": 6}


def test_multiplayer_never_runs_rule_checks() -> None:
    state = {"clock": 6}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state, participant_count=2)

    assert result.payload is None
    assert state == {"clock": 6}


def test_a_bad_expression_is_isolated() -> None:
    broken = _check("broken", {"field": "clock", "op": "explode", "value": 1})
    good = _check("good", CLOCK_PAST_5, priority=1)
    state = {"clock": 6}

    result = _run(_snapshot(broken, good), state)

    assert result.payload.prompt == "Prompt good"


def test_a_queued_check_deleted_from_the_snapshot_is_skipped() -> None:
    state = {"clock": 0, "_check_queue": ["ghost"]}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state)

    assert result.payload is None
    assert state["_check_queue"] == []


def test_unchanged_bookkeeping_is_not_reported_as_mutated() -> None:
    state = {"clock": 0}

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state)

    assert result.mutated_paths == set()


def _recall_check(check_id: str, trigger: dict) -> dict:
    return _check(
        check_id,
        trigger,
        kind="recall",
        params={
            "prompt": "Which wording?",
            "variants": ["one", "two", "three", "four"],
            "correct_index": 2,
            "window_ms": 30000,
            "result_correct": "answered",
            "result_wrong": "ignored",
            "result_timeout": "ignored",
        },
    )


def test_recall_variants_are_shuffled_with_ids_that_encode_the_original_index() -> None:
    state = {"clock": 6}

    result = _run(_snapshot(_recall_check("r", CLOCK_PAST_5)), state)

    variants = state["_pending_check"]["variants"]
    assert sorted(variant["id"] for variant in variants) == ["v0", "v1", "v2", "v3"]
    assert {variant["id"]: variant["text"] for variant in variants}["v2"] == "three"
    assert result.payload.variants == [
        type(result.payload.variants[0])(**variant) for variant in variants
    ]
    assert state["_pending_check"]["options"] == []


def test_recall_payload_never_carries_the_correct_index_or_results() -> None:
    state = {"clock": 6}

    _run(_snapshot(_recall_check("r", CLOCK_PAST_5)), state)

    serialized = str(state["_pending_check"])
    assert "correct_index" not in serialized
    assert "result_correct" not in serialized


def test_recall_shuffle_is_deterministic_for_one_check_id() -> None:
    from app.turn.rule_check_payload import build_event_payload

    definition = _recall_check("r", CLOCK_PAST_5)

    first = build_event_payload(definition, check_id="same", now_ms=1, reopen_count=0)
    second = build_event_payload(definition, check_id="same", now_ms=2, reopen_count=0)

    assert first.variants == second.variants


def test_a_queued_reopen_consumes_its_count_and_stamps_it() -> None:
    state = {
        "clock": 6,
        "_check_queue": ["a"],
        "_check_edges": ["a"],
        "_check_reopens": {"a": 2},
    }

    result = _run(_snapshot(_check("a", CLOCK_PAST_5)), state)

    assert state["_pending_check"]["reopen_count"] == 2
    assert state["_check_reopens"] == {}
    assert "_check_reopens" in result.mutated_paths


def test_a_fresh_open_starts_at_zero_reopens() -> None:
    state = {"clock": 6}

    _run(_snapshot(_check("a", CLOCK_PAST_5)), state)

    assert state["_pending_check"]["reopen_count"] == 0
    assert state["_pending_check"]["hidden_grace_ms"] == 1500
