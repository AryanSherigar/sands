"""The validator must catch the mistakes the generator can make."""

import dataclasses

import pytest
from app.models.condition import ConditionCreate
from app.models.end_condition import EndConditionCreate
from scripts.reincarnated_aristocrat.builder import AppraisalScenario, build
from scripts.reincarnated_aristocrat.ids import entity_id
from scripts.reincarnated_aristocrat.validation import validate
from scripts.seeding.expr import Cond, Mut, eq, gte, to_condition


@pytest.fixture(scope="module")
def built() -> AppraisalScenario:
    return build()


def _with_conditions(
    built: AppraisalScenario, *extra: ConditionCreate
) -> AppraisalScenario:
    return dataclasses.replace(built, conditions=[*built.conditions, *extra])


def _condition(label: str, expression: dict[str, object], *mutations: Mut):
    return to_condition(Cond(label, expression, mutations, "x"))


def test_the_generated_scenario_has_no_problems(built: AppraisalScenario) -> None:
    assert validate(built) == []


def test_unknown_state_field_is_reported(built: AppraisalScenario) -> None:
    bad = _condition("W99 bad", eq("time.nope", 1))
    assert any("time.nope" in item for item in validate(_with_conditions(built, bad)))


def test_unknown_character_attribute_is_reported(built: AppraisalScenario) -> None:
    bad = _condition("W99 bad", eq(f"{entity_id('ritsu')}.nope", 1))
    assert any("nope" in item for item in validate(_with_conditions(built, bad)))


def test_enum_value_outside_the_options_is_reported(built: AppraisalScenario) -> None:
    bad = _condition("W99 bad", eq("intent.train_who", "nobody"))
    assert any(
        "not in options" in item for item in validate(_with_conditions(built, bad))
    )


def test_setting_an_enum_to_an_unknown_value_is_reported(
    built: AppraisalScenario,
) -> None:
    bad = _condition(
        "W99 bad", eq("funds", 1), Mut("intent.time_cost", "set", "forever")
    )
    assert any("not in" in item for item in validate(_with_conditions(built, bad)))


def test_mutating_an_undeclared_path_is_reported(built: AppraisalScenario) -> None:
    bad = _condition("W99 bad", eq("funds", 1), Mut("treasury", "set", 1))
    assert any("treasury" in item for item in validate(_with_conditions(built, bad)))


def test_a_numeric_comparison_on_text_is_reported(built: AppraisalScenario) -> None:
    bad = _condition("W99 bad", gte("intent.train_who", 1))
    assert any("non-number" in item for item in validate(_with_conditions(built, bad)))


def test_incrementing_a_flag_is_reported(built: AppraisalScenario) -> None:
    bad = _condition("W99 bad", eq("funds", 1), Mut("beats.engaged", "increment", 1))
    assert any("non-number" in item for item in validate(_with_conditions(built, bad)))


def test_a_literal_write_beyond_a_fields_range_is_reported(
    built: AppraisalScenario,
) -> None:
    bad = _condition("W99 bad", eq("funds", 1), Mut("control", "set", 500))
    assert any(
        "out of range" in item for item in validate(_with_conditions(built, bad))
    )


def test_a_literal_write_beyond_a_characters_cap_is_reported(
    built: AppraisalScenario,
) -> None:
    path = f"{entity_id('ritsu')}.leadership"
    bad = _condition("W99 bad", eq("funds", 1), Mut(path, "set", 500))
    assert any(
        "out of range" in item for item in validate(_with_conditions(built, bad))
    )


def test_a_duplicate_label_is_reported(built: AppraisalScenario) -> None:
    duplicate = _condition(built.conditions[-1].label, eq("funds", 1))
    assert any(
        "duplicate label" in item
        for item in validate(_with_conditions(built, duplicate))
    )


def test_a_condition_out_of_group_order_is_reported(built: AppraisalScenario) -> None:
    early = _condition("G99 late", eq("funds", 1))
    assert any(
        "breaks group order" in item
        for item in validate(_with_conditions(built, early))
    )


def test_a_condition_with_no_effect_is_reported(built: AppraisalScenario) -> None:
    empty = to_condition(Cond("W99 empty", eq("funds", 1)))
    assert any(
        "no mutation" in item for item in validate(_with_conditions(built, empty))
    )


def test_an_ending_that_reads_an_unknown_field_is_reported(
    built: AppraisalScenario,
) -> None:
    bad = EndConditionCreate(
        condition_expression=eq("time.nope", 1),
        outcome_tag="lose",
        outcome_title="Bad",
        outcome_text="x",
    )
    broken = dataclasses.replace(built, end_conditions=[*built.end_conditions, bad])
    assert any("time.nope" in item for item in validate(broken))
