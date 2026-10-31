import pytest
from app.engine.conditions import UnsupportedMetricError, evaluate
from app.engine.subjects import Subject
from app.models.world_character import GovernorState
from strategy_contracts.conditions import (
    SUBJECT_PLACEHOLDER,
    AllOf,
    AnyOf,
    Comparison,
    ConditionMetric,
    ConditionOperator,
    ConditionScope,
    Negation,
)

from tests.models.builders import make_world

PLAYER = "house_carrow"
RIVAL = "house_ashford"
TREASURY_FLOOR = 50
STABILITY_FLOOR = 40
EXHAUSTION_CEILING = 30
CURRENT_TURN = 4

UNSUPPORTED_METRICS = [
    ConditionMetric.OWNS_REGION,
    ConditionMetric.HOLDS_CAPITAL_OF,
    ConditionMetric.IS_RULER_ALIVE,
    ConditionMetric.IS_AT_PEACE_WITH_ALL,
]


def _compare(
    metric: ConditionMetric,
    operator: ConditionOperator,
    value: int,
    subject_id: str | None = None,
) -> Comparison:
    return Comparison(
        metric=metric, operator=operator, value=value, subject_id=subject_id
    )


def _world():
    world = make_world()
    world.clock.turn = CURRENT_TURN
    world.factions[PLAYER].treasury = TREASURY_FLOOR
    world.factions[PLAYER].stability = STABILITY_FLOOR
    world.factions[PLAYER].war_exhaustion = EXHAUSTION_CEILING
    return world


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        (ConditionMetric.TURN, CURRENT_TURN),
        (ConditionMetric.TREASURY, TREASURY_FLOOR),
        (ConditionMetric.STABILITY, STABILITY_FLOOR),
        (ConditionMetric.WAR_EXHAUSTION, EXHAUSTION_CEILING),
    ],
)
def test_metric_reads_the_players_own_value_by_default(
    metric: ConditionMetric, expected: int
) -> None:
    condition = _compare(metric, ConditionOperator.EQ, expected)
    assert evaluate(_world(), condition)
    off_by_one = _compare(metric, ConditionOperator.EQ, expected + 1)
    assert not evaluate(_world(), off_by_one)


def test_subject_id_selects_another_faction() -> None:
    world = _world()
    world.factions[RIVAL].treasury = TREASURY_FLOOR + 7
    condition = _compare(
        ConditionMetric.TREASURY, ConditionOperator.EQ, TREASURY_FLOOR + 7, RIVAL
    )
    assert evaluate(world, condition)


def test_region_count_counts_only_the_factions_regions() -> None:
    world = _world()
    owned = sum(1 for region in world.regions.values() if region.owner_id == PLAYER)
    condition = _compare(ConditionMetric.REGION_COUNT, ConditionOperator.EQ, owned)
    assert evaluate(world, condition)


def test_destroyed_flag_reads_as_one_or_zero() -> None:
    world = _world()
    destroyed = _compare(ConditionMetric.IS_FACTION_DESTROYED, ConditionOperator.EQ, 1)
    assert not evaluate(world, destroyed)
    world.factions[PLAYER].is_destroyed = True
    assert evaluate(world, destroyed)


def test_unknown_faction_is_an_error_not_zero() -> None:
    condition = _compare(
        ConditionMetric.TREASURY, ConditionOperator.GTE, 0, "house_nowhere"
    )
    with pytest.raises(UnsupportedMetricError):
        evaluate(_world(), condition)


@pytest.mark.parametrize("metric", UNSUPPORTED_METRICS)
def test_unsupported_metrics_raise_instead_of_returning_the_region_count(
    metric: ConditionMetric,
) -> None:
    condition = _compare(metric, ConditionOperator.GTE, 0)
    with pytest.raises(UnsupportedMetricError):
        evaluate(_world(), condition)


def test_all_of_any_of_and_not_combine() -> None:
    world = _world()
    rich = _compare(ConditionMetric.TREASURY, ConditionOperator.GTE, TREASURY_FLOOR)
    unstable = _compare(
        ConditionMetric.STABILITY, ConditionOperator.LT, STABILITY_FLOOR
    )
    assert evaluate(world, AnyOf(conditions=[rich, unstable]))
    assert not evaluate(world, AllOf(conditions=[rich, unstable]))
    assert evaluate(world, AllOf(conditions=[rich, Negation(condition=unstable)]))


def test_empty_any_of_is_false_and_empty_all_of_is_true() -> None:
    world = _world()
    assert not evaluate(world, AnyOf(conditions=[]))
    assert evaluate(world, AllOf(conditions=[]))


def test_entity_metrics_read_the_bound_subject_and_its_relations() -> None:

    world = _world()
    world.regions["carrow_vale"].unrest = 55
    world.regions["carrow_vale"].governor_id = "gov_a"
    world.governors["gov_a"] = GovernorState(
        id="gov_a", name="Harl", region_id="carrow_vale", opinion_of_ruler=-40
    )
    unrest = _compare(
        ConditionMetric.REGION_UNREST, ConditionOperator.EQ, 55, SUBJECT_PLACEHOLDER
    )
    opinion = _compare(
        ConditionMetric.GOVERNOR_OPINION, ConditionOperator.EQ, -40, SUBJECT_PLACEHOLDER
    )
    region = Subject(ConditionScope.REGION, "carrow_vale")
    governor = Subject(ConditionScope.GOVERNOR, "gov_a")
    assert evaluate(world, unrest, subject=region)
    assert evaluate(world, unrest, subject=governor)
    assert evaluate(world, opinion, subject=region)
    assert evaluate(world, opinion, subject=governor)


def test_entity_metric_with_no_related_entity_is_false_not_an_error() -> None:

    world = _world()
    opinion = _compare(
        ConditionMetric.GOVERNOR_OPINION,
        ConditionOperator.LTE,
        100,
        SUBJECT_PLACEHOLDER,
    )
    region = Subject(ConditionScope.REGION, "carrow_vale")
    assert not evaluate(world, opinion, subject=region)


def test_entity_metric_without_a_subject_is_an_error() -> None:

    unrest = _compare(
        ConditionMetric.REGION_UNREST, ConditionOperator.GTE, 0, SUBJECT_PLACEHOLDER
    )
    with pytest.raises(UnsupportedMetricError):
        evaluate(_world(), unrest)


def test_regions_in_unrest_counts_only_the_factions_regions_above_threshold() -> None:
    world = _world()
    world.regions["carrow_vale"].unrest = 70
    world.regions["ashford"].unrest = 90
    condition = Comparison(
        metric=ConditionMetric.REGIONS_WITH_UNREST_AT_LEAST,
        operator=ConditionOperator.EQ,
        value=1,
        threshold=60,
    )
    assert evaluate(world, condition)


def test_month_wraps_the_year() -> None:
    from app.models.world_clock import TurnClock, current_month

    months = [
        current_month(TurnClock(turn=turn, start_year=1000, start_month=11))
        for turn in range(3)
    ]

    assert months == [11, 1, 3]


def test_month_metric_reads_through_a_comparison() -> None:
    from app.engine.conditions import evaluate
    from strategy_contracts.conditions import (
        Comparison,
        ConditionMetric,
        ConditionOperator,
    )

    from tests.models.builders import make_world

    world = make_world()
    world.clock.start_month = 9
    comparison = Comparison(
        metric=ConditionMetric.MONTH, operator=ConditionOperator.EQ, value=9
    )

    assert evaluate(world, comparison, faction_id="house_carrow") is True
