from app.models.world_events import EndingState
from app.services.world_projection import project_ending
from strategy_contracts.conditions import (
    Comparison,
    ConditionMetric,
    ConditionOperator,
)
from strategy_contracts.endings import EndingGrade
from strategy_contracts.scenario import EndingDefinition, EndingKind, StrategyScenario
from tests.models.builders import make_world


def test_ending_view_has_the_grade_but_no_inputs() -> None:
    world = make_world()
    world.ending = EndingState(
        ending_id="default_graded_end_date",
        kind=EndingKind.GRADED,
        turn=29,
        grade=EndingGrade.TRIUMPH,
        inputs={"score": 91, "region_share": 80},
    )
    view = project_ending(world)
    assert view is not None
    document = view.model_dump(mode="json")
    assert document["grade"] == "triumph"
    assert "inputs" not in document
    assert "score" not in str(document)


def test_ending_view_for_a_defeat_has_no_grade() -> None:
    world = make_world()
    world.ending = EndingState(
        ending_id="default_defeat_capital_lost", kind=EndingKind.DEFEAT, turn=2
    )
    view = project_ending(world)
    assert view is not None
    assert view.model_dump(mode="json")["ending_id"] == "default_defeat_capital_lost"
    assert "grade" not in view.model_dump(mode="json")


def test_a_running_world_has_no_ending_view() -> None:
    assert project_ending(make_world()) is None


def test_a_creator_ending_shows_its_authored_name() -> None:
    world = make_world()
    world.ending = EndingState(ending_id="golden_age", kind=EndingKind.VICTORY, turn=9)
    scenario = StrategyScenario(
        is_using_default_endings=False,
        endings=[
            EndingDefinition(
                id="golden_age",
                kind=EndingKind.VICTORY,
                name="The Golden Age",
                condition=Comparison(
                    metric=ConditionMetric.TREASURY,
                    operator=ConditionOperator.GTE,
                    value=1,
                ),
            )
        ],
    )

    view = project_ending(world, scenario)

    assert view is not None
    assert view.model_dump(mode="json")["name"] == "The Golden Age"
    assert "name" not in project_ending(world).model_dump(mode="json")
