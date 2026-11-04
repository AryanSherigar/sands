import pytest
from app.models.rule_check import (
    RULE_CHECK_KINDS,
    RecallParams,
    RuleCheckCreate,
    RuleCheckUpdate,
    TimedChoiceParams,
    TimeEntryParams,
)
from pydantic import ValidationError


def _option(option_id: str = "answer", **overrides) -> dict[str, object]:
    base = {"id": option_id, "label": "Answer it", "result": "answered"}
    base.update(overrides)
    return base


def _params(**overrides) -> dict[str, object]:
    base = {
        "prompt": "The phone rings.",
        "options": [
            _option("answer"),
            _option("ignore", label="Ignore it", result="ignored"),
        ],
        "window_ms": 12000,
        "timeout_result": "ignored",
    }
    base.update(overrides)
    return base


def _create(**overrides) -> RuleCheckCreate:
    base = {
        "label": "03:14 phone",
        "kind": "timed_choice",
        "trigger_condition_expression": {"field": "clock", "op": ">=", "value": 5},
        "result_path": "rule_r3",
        "params": _params(),
    }
    base.update(overrides)
    return RuleCheckCreate(**base)


def test_timed_choice_recall_and_time_entry_are_the_kinds() -> None:
    assert RULE_CHECK_KINDS == ("timed_choice", "recall", "time_entry")


def _time_entry_params(**overrides: object) -> dict[str, object]:
    outcome = {"result": "told", "mutations": []}
    params: dict[str, object] = {
        "prompt": "Write the time.",
        "told_minute_of_day": 1432,
        "clock_path": "shift_minutes",
        "clock_start_minute_of_day": 1380,
        "window_ms": 45_000,
        "timeout_result": "none",
        "told": outcome,
        "wall": {"result": "wall", "mutations": []},
        "other": {"result": "other", "mutations": []},
        "reject": {"result": "rejected", "mutations": []},
    }
    return {**params, **overrides}


def test_time_entry_params_list_every_result_and_default_the_labels() -> None:
    params = TimeEntryParams.model_validate(_time_entry_params())

    assert params.result_values() == ["told", "wall", "other", "rejected", "none"]
    assert params.reject_label == "Reject the visitor"


def test_time_entry_rejects_a_told_time_outside_the_day() -> None:
    with pytest.raises(ValidationError):
        TimeEntryParams.model_validate(_time_entry_params(told_minute_of_day=1440))


def test_time_entry_collects_mutation_paths_from_every_outcome() -> None:
    mutation = {"path": "counters.defiance", "op": "increment", "value": 1}
    params = TimeEntryParams.model_validate(
        _time_entry_params(reject={"result": "rejected", "mutations": [mutation]})
    )

    assert params.mutation_paths() == ["counters.defiance"]


def test_valid_timed_choice_is_accepted_and_defaults_priority() -> None:
    check = _create()

    assert check.priority == 0
    assert check.params["window_ms"] == 12000


def test_unknown_kind_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _create(kind="quiz")


def test_at_least_two_options_are_required() -> None:
    with pytest.raises(ValidationError):
        _create(params=_params(options=[_option()]))


def test_at_most_six_options_are_allowed() -> None:
    options = [_option(f"opt{i}", result=f"r{i}") for i in range(7)]

    with pytest.raises(ValidationError):
        _create(params=_params(options=options))


@pytest.mark.parametrize("window_ms", [999, 120_001])
def test_window_outside_1_to_120_seconds_is_rejected(window_ms: int) -> None:
    with pytest.raises(ValidationError):
        _create(params=_params(window_ms=window_ms))


def test_duplicate_option_ids_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _create(params=_params(options=[_option("same"), _option("same")]))


@pytest.mark.parametrize("bad_id", ["Answer", "1abc", "has space", "x" * 32])
def test_option_id_pattern_is_enforced(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        _create(params=_params(options=[_option(bad_id), _option("other")]))


def test_prompt_and_labels_have_length_caps() -> None:
    with pytest.raises(ValidationError):
        _create(params=_params(prompt="x" * 501))
    with pytest.raises(ValidationError):
        _create(params=_params(options=[_option(label="y" * 121), _option("other")]))


def test_option_mutations_are_capped_at_eight() -> None:
    mutation = {"path": "sanity", "op": "decrement", "value": 1}

    with pytest.raises(ValidationError):
        _create(
            params=_params(
                options=[_option(mutations=[mutation] * 9), _option("other")]
            )
        )


def test_unknown_param_keys_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _create(params=_params(window_seconds=12))


def test_params_are_normalised_through_the_model() -> None:
    check = _create(
        params=_params(
            options=[
                _option(mutations=[{"path": "sanity", "op": "set", "value": 3}]),
                _option("b"),
            ]
        )
    )

    assert check.params["options"][0]["mutations"] == [
        {"path": "sanity", "op": "set", "value": 3}
    ]


def test_timed_choice_params_model_is_exported_for_reuse() -> None:
    assert TimedChoiceParams.model_validate(_params()).window_ms == 12000


def test_update_does_not_require_any_field() -> None:
    assert RuleCheckUpdate().model_fields_set == set()


def test_reopening_and_hidden_result_default_to_off_and_three_reopens() -> None:
    params = TimedChoiceParams.model_validate(_params())

    assert params.hidden_result is None
    assert params.max_reopens == 3
    assert params.options[0].reopens is False


def test_hidden_result_counts_as_a_result_value() -> None:
    params = TimedChoiceParams.model_validate(_params(hidden_result="moved"))

    assert "moved" in params.result_values()


@pytest.mark.parametrize("max_reopens", [-1, 11])
def test_max_reopens_is_bounded(max_reopens: int) -> None:
    with pytest.raises(ValidationError):
        TimedChoiceParams.model_validate(_params(max_reopens=max_reopens))


def test_an_option_can_reopen_the_check() -> None:
    options = [_option("ask", reopens=True), _option("hang", result="ignored")]

    params = TimedChoiceParams.model_validate(_params(options=options))

    assert params.options[0].reopens is True


def _recall(**overrides) -> dict[str, object]:
    base = {
        "prompt": "Which wording was the original rule?",
        "variants": ["Never answer", "Always answer", "Answer once"],
        "correct_index": 1,
        "result_correct": "answered",
        "result_wrong": "ignored",
        "result_timeout": "unseen",
    }
    base.update(overrides)
    return base


def test_recall_check_is_accepted_with_a_default_window() -> None:
    check = _create(kind="recall", params=_recall())

    assert check.params["window_ms"] == 30_000
    assert check.params["correct_index"] == 1


def test_recall_results_and_no_mutation_paths() -> None:
    params = RecallParams.model_validate(_recall())

    assert params.result_values() == ["answered", "ignored", "unseen"]
    assert params.mutation_paths() == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"variants": ["only one"], "correct_index": 0},
        {"variants": ["a", "b", "c", "d", "e", "f"]},
        {"correct_index": 3},
        {"correct_index": -1},
        {"variants": ["same", "same"], "correct_index": 0},
        {"variants": ["a", " "], "correct_index": 0},
        {"variants": ["a", "x" * 201], "correct_index": 0},
        {"window_ms": 4_999},
        {"window_ms": 120_001},
    ],
)
def test_invalid_recall_params_are_rejected(overrides) -> None:
    with pytest.raises(ValidationError):
        _create(kind="recall", params=_recall(**overrides))


def test_recall_kind_rejects_timed_choice_params() -> None:
    with pytest.raises(ValidationError):
        _create(kind="recall", params=_params())
