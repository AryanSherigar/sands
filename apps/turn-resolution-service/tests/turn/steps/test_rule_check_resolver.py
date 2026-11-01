"""Server-side judging and resolution of rule-check reports."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.exceptions.turn_exceptions import (
    CheckReportInvalidError,
    CheckResolutionMismatchError,
)
from app.models.check_event import CheckReportInput
from app.turn.steps import rule_check_resolver

ISSUED_AT = 1_760_000_000_000
WINDOW_MS = 12_000
TOLERANCE_MS = 3_500

DEFINITION = {
    "check_id": "def-1",
    "label": "03:14 phone",
    "kind": "timed_choice",
    "result_path": "rules.r3",
    "params": {
        "prompt": "The phone rings.",
        "options": [
            {
                "id": "answer",
                "label": "Answer",
                "result": "answered",
                "mutations": [{"path": "sanity", "op": "decrement", "value": 10}],
            },
            {"id": "ignore", "label": "Ignore", "result": "ignored", "mutations": []},
        ],
        "window_ms": WINDOW_MS,
        "timeout_result": "ignored",
    },
    "narrator_instruction_template": None,
}

SNAPSHOT = {
    "enabled_tools": ["rule_checks"],
    "state_schema": {
        "sanity": {"type": "number", "min": 0, "max": 100},
        "alarm": {"type": "boolean"},
        "rules": {
            "type": "object",
            "fields": {
                "r3": {"type": "enum", "options": ["answered", "ignored", "unseen"]}
            },
        },
    },
    "entities": [],
    "rule_invariants": [],
    "rule_checks": [DEFINITION],
}


def _pending(**overrides) -> dict:
    base = {
        "check_id": "chk-1",
        "kind": "timed_choice",
        "check_def_id": "def-1",
        "prompt": "The phone rings.",
        "options": [
            {"id": "answer", "label": "Answer"},
            {"id": "ignore", "label": "Ignore"},
        ],
        "window_ms": WINDOW_MS,
        "issued_at": ISSUED_AT,
        "resolved": None,
    }
    base.update(overrides)
    return base


def _state(pending: dict | None = None) -> dict:
    return {
        "sanity": 50,
        "alarm": False,
        "rules": {"r3": "unseen"},
        "_pending_check": pending if pending is not None else _pending(),
    }


def _report(**fields) -> CheckReportInput:
    return CheckReportInput(check_id="chk-1", **fields)


@pytest.mark.parametrize(
    ("report", "elapsed_ms", "expected_option", "expected_timeout"),
    [
        (_report(choice_id="answer"), 2_000, "answer", False),
        (_report(choice_id="answer"), WINDOW_MS + TOLERANCE_MS, "answer", False),
        (_report(choice_id="answer"), WINDOW_MS + TOLERANCE_MS + 1, None, True),
        (_report(timed_out=True), 12_000, None, True),
        (_report(choice_id="answer", timed_out=True), 12_000, None, True),
    ],
)
def test_judging_matrix(report, elapsed_ms, expected_option, expected_timeout) -> None:
    judgment = rule_check_resolver.judge_report(
        _pending(), report, now_ms=ISSUED_AT + elapsed_ms
    )

    assert judgment.option_id == expected_option
    assert judgment.is_timeout is expected_timeout


def test_unknown_option_is_rejected() -> None:
    with pytest.raises(CheckReportInvalidError):
        rule_check_resolver.judge_report(
            _pending(), _report(choice_id="sprint"), now_ms=ISSUED_AT + 1000
        )


def test_a_timed_choice_option_named_enter_is_a_plain_choice() -> None:
    pending = _pending(
        options=[
            {"id": "hold", "label": "Hold still"},
            {"id": "enter", "label": "Go in"},
        ]
    )

    judgment = rule_check_resolver.judge_report(
        pending, _report(choice_id="enter"), now_ms=ISSUED_AT + 1000
    )

    assert judgment.option_id == "enter"
    assert judgment.entry_text is None
    assert judgment.is_timeout is False


def test_report_with_no_choice_and_no_timeout_is_rejected() -> None:
    with pytest.raises(CheckReportInvalidError):
        rule_check_resolver.judge_report(_pending(), _report(), now_ms=ISSUED_AT + 1000)


async def test_early_persist_stamps_the_judgment_and_commits_once() -> None:
    repo = AsyncMock()
    state = _state()

    updated = await rule_check_resolver.ensure_report_persisted(
        uuid.uuid4(),
        state,
        _report(choice_id="answer"),
        now_ms=ISSUED_AT + 2_000,
        playthrough_repo=repo,
        expected_turn_count=4,
    )

    assert updated["_pending_check"]["resolved"] == {
        "option_id": "answer",
        "is_timeout": False,
        "is_hidden": False,
    }
    repo.update_state.assert_awaited_once()
    repo.session.commit.assert_awaited_once()
    assert state["_pending_check"]["resolved"] is None


async def test_early_persist_never_stores_the_result_string() -> None:
    updated = await rule_check_resolver.ensure_report_persisted(
        uuid.uuid4(),
        _state(),
        _report(choice_id="answer"),
        now_ms=ISSUED_AT + 2_000,
        playthrough_repo=AsyncMock(),
        expected_turn_count=4,
    )

    assert "answered" not in str(updated["_pending_check"])


async def test_retry_replays_the_stored_judgment_even_if_the_new_report_differs() -> (
    None
):
    repo = AsyncMock()
    stored = _pending(resolved={"option_id": "answer", "is_timeout": False})

    updated = await rule_check_resolver.ensure_report_persisted(
        uuid.uuid4(),
        _state(stored),
        _report(timed_out=True),
        now_ms=ISSUED_AT + 60_000,
        playthrough_repo=repo,
        expected_turn_count=4,
    )

    assert updated["_pending_check"]["resolved"]["option_id"] == "answer"
    repo.update_state.assert_not_called()


def _resolved(
    option_id: str | None, is_timeout: bool = False, is_hidden: bool = False
) -> dict:
    return _state(
        _pending(
            resolved={
                "option_id": option_id,
                "is_timeout": is_timeout,
                "is_hidden": is_hidden,
            }
        )
    )


def test_choosing_an_option_writes_its_result_and_mutations() -> None:
    resolution = rule_check_resolver.resolve_report(_resolved("answer"), SNAPSHOT)

    assert resolution.state["rules"]["r3"] == "answered"
    assert resolution.state["sanity"] == 40
    assert "_pending_check" not in resolution.state
    assert resolution.mutated_paths == {"rules.r3", "sanity", "_pending_check"}


def test_timeout_writes_the_timeout_result_and_skips_option_mutations() -> None:
    resolution = rule_check_resolver.resolve_report(_resolved(None, True), SNAPSHOT)

    assert resolution.state["rules"]["r3"] == "ignored"
    assert resolution.state["sanity"] == 50
    assert resolution.mutated_paths == {"rules.r3", "_pending_check"}


def test_an_invalid_option_mutation_is_skipped_alone() -> None:
    definition = {
        **DEFINITION,
        "params": {
            **DEFINITION["params"],
            "options": [
                {
                    "id": "answer",
                    "label": "Answer",
                    "result": "answered",
                    "mutations": [
                        {"path": "sanity", "op": "set", "value": 500},
                        {"path": "alarm", "op": "set", "value": True},
                    ],
                },
                DEFINITION["params"]["options"][1],
            ],
        },
    }
    snapshot = {**SNAPSHOT, "rule_checks": [definition]}

    resolution = rule_check_resolver.resolve_report(_resolved("answer"), snapshot)

    assert resolution.state["sanity"] == 50
    assert resolution.state["alarm"] is True
    assert resolution.state["rules"]["r3"] == "answered"
    assert "sanity" not in resolution.mutated_paths


def test_default_instruction_names_the_check_and_result_without_judging() -> None:
    resolution = rule_check_resolver.resolve_report(_resolved("answer"), SNAPSHOT)

    assert "03:14 phone" in resolution.instruction
    assert "answered" in resolution.instruction
    assert "without commenting on whether it was right" in resolution.instruction


def test_authored_template_tokens_are_substituted() -> None:
    definition = {
        **DEFINITION,
        "narrator_instruction_template": "{label} ended as {result}.",
    }
    snapshot = {**SNAPSHOT, "rule_checks": [definition]}

    resolution = rule_check_resolver.resolve_report(_resolved("answer"), snapshot)

    assert resolution.instruction == "03:14 phone ended as answered."


def test_a_check_deleted_from_the_snapshot_still_clears_the_pending_state() -> None:
    snapshot = {**SNAPSHOT, "rule_checks": []}

    resolution = rule_check_resolver.resolve_report(_resolved("answer"), snapshot)

    assert "_pending_check" not in resolution.state
    assert resolution.mutated_paths == {"_pending_check"}
    assert resolution.state["rules"]["r3"] == "unseen"


def test_resolving_does_not_mutate_the_input_state() -> None:
    state = _resolved("answer")

    rule_check_resolver.resolve_report(state, SNAPSHOT)

    assert state["rules"]["r3"] == "unseen"
    assert "_pending_check" in state


HIDDEN_DEFINITION = {
    **DEFINITION,
    "params": {**DEFINITION["params"], "hidden_result": "unseen"},
}
HIDDEN_SNAPSHOT = {**SNAPSHOT, "rule_checks": [HIDDEN_DEFINITION]}


def test_hidden_tab_is_flagged_on_a_timed_choice_report() -> None:
    judgment = rule_check_resolver.judge_report(
        _pending(),
        _report(choice_id="answer", was_hidden=True),
        now_ms=ISSUED_AT + 1000,
    )

    assert judgment.is_hidden is True
    assert judgment.option_id == "answer"


def test_untimed_mode_ignores_the_hidden_flag_and_lateness() -> None:
    judgment = rule_check_resolver.judge_report(
        _pending(),
        _report(choice_id="answer", was_hidden=True, is_untimed=True),
        now_ms=ISSUED_AT + 10 * WINDOW_MS,
    )

    assert judgment.is_hidden is False
    assert judgment.is_timeout is False
    assert judgment.option_id == "answer"


def test_a_late_report_is_a_plain_timeout_even_when_hidden() -> None:
    judgment = rule_check_resolver.judge_report(
        _pending(),
        _report(choice_id="answer", was_hidden=True),
        now_ms=ISSUED_AT + WINDOW_MS + TOLERANCE_MS + 1,
    )

    assert judgment.is_timeout is True
    assert judgment.is_hidden is False


def test_hidden_report_with_a_hidden_result_writes_it_and_skips_mutations() -> None:
    resolution = rule_check_resolver.resolve_report(
        _resolved("answer", is_hidden=True), HIDDEN_SNAPSHOT
    )

    assert resolution.state["rules"]["r3"] == "unseen"
    assert resolution.state["sanity"] == 50


def test_hidden_report_with_no_hidden_result_has_no_penalty() -> None:
    resolution = rule_check_resolver.resolve_report(
        _resolved("answer", is_hidden=True), SNAPSHOT
    )

    assert resolution.state["rules"]["r3"] == "answered"
    assert resolution.state["sanity"] == 40


def test_hidden_wins_over_a_client_timer_expiry() -> None:
    resolution = rule_check_resolver.resolve_report(
        _resolved(None, is_timeout=True, is_hidden=True), HIDDEN_SNAPSHOT
    )

    assert resolution.state["rules"]["r3"] == "unseen"


RECALL_DEFINITION = {
    "check_id": "def-recall",
    "label": "Which wording",
    "kind": "recall",
    "result_path": "rules.r3",
    "params": {
        "prompt": "Which wording was the original rule?",
        "variants": ["Never answer", "Always answer", "Answer once"],
        "correct_index": 1,
        "window_ms": 30_000,
        "result_correct": "answered",
        "result_wrong": "ignored",
        "result_timeout": "unseen",
    },
    "narrator_instruction_template": None,
}
RECALL_SNAPSHOT = {**SNAPSHOT, "rule_checks": [RECALL_DEFINITION]}


def _recall_pending(**overrides) -> dict:
    return _pending(
        kind="recall",
        check_def_id="def-recall",
        options=[],
        variants=[
            {"id": "v2", "text": "Answer once"},
            {"id": "v0", "text": "Never answer"},
            {"id": "v1", "text": "Always answer"},
        ],
        window_ms=30_000,
        **overrides,
    )


def test_recall_choice_must_be_one_of_the_shown_variants() -> None:
    with pytest.raises(CheckReportInvalidError):
        rule_check_resolver.judge_report(
            _recall_pending(), _report(choice_id="v9"), now_ms=ISSUED_AT + 1000
        )


def test_recall_hidden_flag_is_never_set() -> None:
    judgment = rule_check_resolver.judge_report(
        _recall_pending(),
        _report(choice_id="v1", was_hidden=True),
        now_ms=ISSUED_AT + 1000,
    )

    assert judgment.is_hidden is False


@pytest.mark.parametrize(
    ("option_id", "is_timeout", "expected"),
    [("v1", False, "answered"), ("v0", False, "ignored"), (None, True, "unseen")],
)
def test_recall_outcomes_follow_the_snapshot_correct_index(
    option_id, is_timeout, expected
) -> None:
    resolved = {"option_id": option_id, "is_timeout": is_timeout, "is_hidden": False}
    state = _state(_recall_pending(resolved=resolved))

    resolution = rule_check_resolver.resolve_report(state, RECALL_SNAPSHOT)

    assert resolution.state["rules"]["r3"] == expected


REOPEN_DEFINITION = {
    **DEFINITION,
    "params": {
        **DEFINITION["params"],
        "max_reopens": 2,
        "options": [
            {
                "id": "ask",
                "label": "Ask who it is",
                "result": "answered",
                "mutations": [],
                "reopens": True,
            },
            DEFINITION["params"]["options"][1],
        ],
    },
}
REOPEN_SNAPSHOT = {**SNAPSHOT, "rule_checks": [REOPEN_DEFINITION]}


def _reopening_state(reopen_count: int) -> dict:
    resolved = {"option_id": "ask", "is_timeout": False, "is_hidden": False}
    state = _state(_pending(resolved=resolved, reopen_count=reopen_count))
    return {**state, "_check_queue": ["other"]}


def test_a_reopening_option_queues_the_check_at_the_front() -> None:
    resolution = rule_check_resolver.resolve_report(
        _reopening_state(0), REOPEN_SNAPSHOT
    )

    assert resolution.state["_check_queue"] == ["def-1", "other"]
    assert resolution.state["_check_reopens"] == {"def-1": 1}
    assert {"_check_queue", "_check_reopens"} <= resolution.mutated_paths


def test_reopening_stops_at_max_reopens() -> None:
    resolution = rule_check_resolver.resolve_report(
        _reopening_state(2), REOPEN_SNAPSHOT
    )

    assert resolution.state["_check_queue"] == ["other"]
    assert "_check_reopens" not in resolution.state


def test_a_timeout_on_a_reopening_check_does_not_reopen() -> None:
    resolved = {"option_id": None, "is_timeout": True, "is_hidden": False}
    state = _state(_pending(resolved=resolved, reopen_count=0))

    resolution = rule_check_resolver.resolve_report(state, REOPEN_SNAPSHOT)

    assert "_check_reopens" not in resolution.state


def _locked_repo(state: dict) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_id_for_update.return_value = SimpleNamespace(state=state)
    return repo


async def test_persist_reads_the_row_under_lock_and_replays_a_winner() -> None:
    winner = _pending(
        resolved={"option_id": "ignore", "is_timeout": False, "is_hidden": False}
    )
    repo = _locked_repo(_state(winner))

    updated = await rule_check_resolver.ensure_report_persisted(
        uuid.uuid4(),
        _state(),
        _report(choice_id="answer"),
        now_ms=ISSUED_AT + 2_000,
        playthrough_repo=repo,
        expected_turn_count=4,
    )

    repo.get_by_id_for_update.assert_awaited_once()
    assert updated["_pending_check"]["resolved"]["option_id"] == "ignore"
    repo.update_state.assert_not_called()


async def test_persist_rejects_a_check_that_closed_while_waiting_for_the_lock() -> None:
    repo = _locked_repo({"sanity": 50})

    with pytest.raises(CheckResolutionMismatchError):
        await rule_check_resolver.ensure_report_persisted(
            uuid.uuid4(),
            _state(),
            _report(choice_id="answer"),
            now_ms=ISSUED_AT + 2_000,
            playthrough_repo=repo,
            expected_turn_count=4,
        )


async def test_persist_rejects_a_report_for_a_newer_check() -> None:
    repo = _locked_repo(_state(_pending(check_id="chk-2")))

    with pytest.raises(CheckResolutionMismatchError):
        await rule_check_resolver.ensure_report_persisted(
            uuid.uuid4(),
            _state(),
            _report(choice_id="answer"),
            now_ms=ISSUED_AT + 2_000,
            playthrough_repo=repo,
            expected_turn_count=4,
        )


def test_state_tokens_read_the_state_after_the_option_mutations() -> None:
    definition = {
        **DEFINITION,
        "narrator_instruction_template": "Composure is {state:sanity}.",
    }
    snapshot = {**SNAPSHOT, "rule_checks": [definition]}

    resolution = rule_check_resolver.resolve_report(_resolved("answer"), snapshot)

    assert resolution.instruction == "Composure is 40."


def test_a_missing_state_token_renders_empty() -> None:
    definition = {
        **DEFINITION,
        "narrator_instruction_template": "The difference is {state:count.difference}.",
    }
    snapshot = {**SNAPSHOT, "rule_checks": [definition]}

    resolution = rule_check_resolver.resolve_report(_resolved("answer"), snapshot)

    assert resolution.instruction == "The difference is ."
