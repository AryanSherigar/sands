"""The validator must catch the mistakes the generator can make."""

import dataclasses

import pytest
from app.models.condition import ConditionCreate
from app.models.rule_check import RuleCheckCreate
from scripts.night_desk.builder import NightDeskScenario, build
from scripts.night_desk.expr import Cond, Mut, eq, to_condition
from scripts.night_desk.validation import validate


@pytest.fixture(scope="module")
def built() -> NightDeskScenario:
    return build()


def _with_conditions(
    built: NightDeskScenario, *extra: ConditionCreate
) -> NightDeskScenario:
    return dataclasses.replace(built, conditions=[*built.conditions, *extra])


def _condition(label: str, expression: dict[str, object], *mutations: Mut):
    return to_condition(Cond(label, expression, mutations, "x"))


def test_the_generated_scenario_has_no_problems(built):
    assert validate(built) == []


def test_unknown_field_path_is_reported(built):
    bad = _condition("A99 bad", eq("flags.nope", True))
    problems = validate(_with_conditions(built, bad))
    assert any("flags.nope" in problem for problem in problems)


def test_enum_value_outside_options_is_reported(built):
    bad = _condition("A99 bad", eq("check.lamp", "levitated"))
    problems = validate(_with_conditions(built, bad))
    assert any("not in options" in problem for problem in problems)


def test_mutation_to_an_undeclared_path_is_reported(built):
    bad = _condition("A99 bad", eq("sanity", 1), Mut("flags.nope", "set", True))
    problems = validate(_with_conditions(built, bad))
    assert any("flags.nope" in problem for problem in problems)


def test_set_to_a_value_outside_the_enum_is_reported(built):
    bad = _condition("A99 bad", eq("sanity", 1), Mut("check.lamp", "set", "levitated"))
    problems = validate(_with_conditions(built, bad))
    assert any("not in" in problem for problem in problems)


def test_unknown_entity_id_in_a_location_comparison_is_reported(built):
    bad = _condition("A99 bad", eq("current_location_id", "not-an-id"))
    problems = validate(_with_conditions(built, bad))
    assert any("unknown entity id" in problem for problem in problems)


def test_group_order_violation_is_reported(built):
    late = _condition("E99 late event", eq("sanity", 1))
    problems = validate(_with_conditions(built, late))
    assert any("breaks group order" in problem for problem in problems)


def test_duplicate_labels_are_reported(built):
    duplicate = _condition(built.conditions[-1].label, eq("sanity", 1))
    problems = validate(_with_conditions(built, duplicate))
    assert any("duplicate label" in problem for problem in problems)


def test_a_condition_with_no_effect_is_reported(built):
    empty = ConditionCreate(
        label="A99 empty", condition_expression=eq("sanity", 1), narrator_instruction=""
    )
    problems = validate(_with_conditions(built, empty))
    assert any(
        "no mutation, instruction, cue or effect" in problem for problem in problems
    )


def test_rule_check_result_outside_the_enum_is_reported(built):
    check = built.rule_checks[2]
    params = {**check.params, "timeout_result": "levitated"}
    broken = RuleCheckCreate.model_construct(**{**check.model_dump(), "params": params})
    problems = validate(dataclasses.replace(built, rule_checks=[broken]))
    assert any("levitated" in problem for problem in problems)


def test_tools_that_miss_a_requirement_are_reported(built):
    scenario = {**built.scenario, "enabled_tools": ["atmosphere"]}
    problems = validate(dataclasses.replace(built, scenario=scenario))
    assert any("not closed over requires" in problem for problem in problems)


def test_a_display_hint_on_a_hidden_field_is_reported(built):
    schema = {**built.scenario["state_schema"]}
    schema["violations_count"] = {
        **schema["violations_count"],
        "display": {"kind": "meter", "label": "x", "clamp_min": 0, "clamp_max": 9},
    }
    problems = validate(
        dataclasses.replace(built, scenario={**built.scenario, "state_schema": schema})
    )
    assert any("hidden field cannot be displayed" in problem for problem in problems)


def test_a_content_tag_outside_the_vocabulary_is_reported(built):
    scenario = {**built.scenario, "content_tags": ["mature"]}

    problems = validate(dataclasses.replace(built, scenario=scenario))

    assert any("unknown content_tags" in problem for problem in problems)


def test_a_missing_r6_hand_is_reported(built):
    rules = [rule for rule in built.sheet_rules if rule.key != "r6_block"]
    problems = validate(dataclasses.replace(built, sheet_rules=rules))
    assert any("rule 6 must have one ink and one ink_block row" in p for p in problems)


def test_a_wrong_turn_count_is_reported(built, monkeypatch):
    from scripts.night_desk import timeline

    monkeypatch.setattr(timeline, "EXPECTED_TURN_COUNT", 22)
    assert any("the night is 21 turns" in p for p in validate(built))


def test_an_effect_only_condition_is_not_reported_as_empty(built):
    effect = {
        "kind": "phone_echo",
        "params": {"record_ms": 6000, "delay_ms": 2500},
    }
    only_effect = to_condition(Cond("A98 effect", eq("sanity", 1), effect=effect))
    assert validate(_with_conditions(built, only_effect)) == []
