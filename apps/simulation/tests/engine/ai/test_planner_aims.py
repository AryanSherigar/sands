from app.engine.ai.candidates import Candidate
from app.engine.ai.planner import plan_ai_orders
from app.engine.ai.scoring import score_candidate
from app.models.orders import SetTaxRateOrder
from app.models.world_ai import AimState
from strategy_contracts.enums import TaxRate
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

AIM_BONUS = SCENARIO.tuning.ai.aim_bonus


def _world(stance: str | None = "turtle"):
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].stance.option_id = stance
    world.factions[WRATHFUL_RIVAL].leader_id = None
    return world


def _candidate(category: ScoreCategory) -> Candidate:
    order = SetTaxRateOrder(faction_id=CAUTIOUS_RIVAL, tax_rate=TaxRate.HIGH)
    return Candidate(order=order, category=category)


def _hoard_aim(world) -> AimState:
    return AimState(
        category=ScoreCategory.HOARD,
        chosen_turn=world.clock.turn,
        leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
        stance_option_id=world.factions[CAUTIOUS_RIVAL].stance.option_id,
        capital_held=True,
    )


def test_aim_bonus_applies_only_to_the_aims_category() -> None:
    world = _world()
    world.aims[CAUTIOUS_RIVAL] = _hoard_aim(world)

    hoard = score_candidate(
        world, SCENARIO, CAUTIOUS_RIVAL, _candidate(ScoreCategory.HOARD)
    )
    build = score_candidate(
        world, SCENARIO, CAUTIOUS_RIVAL, _candidate(ScoreCategory.BUILD)
    )

    assert (hoard.aim_score, build.aim_score) == (AIM_BONUS, 0)
    assert hoard.score == hoard.trait_score + hoard.stance_score + AIM_BONUS


def test_planning_sets_an_aim_and_logs_it() -> None:
    plan = plan_ai_orders(_world(), SCENARIO)

    aim = plan.world.aims[CAUTIOUS_RIVAL]
    aim_events = [event for event in plan.events if event.kind == "ai_aim_set"]
    assert [event.cause.summary_key for event in aim_events] == [
        f"ai_aim_{aim.category.value}"
    ]


def test_order_events_carry_the_aim_score_and_because() -> None:
    plan = plan_ai_orders(_world(), SCENARIO)

    order_event = next(e for e in plan.events if e.kind == "ai_order_planned")

    assert order_event.cause.inputs["aim_score"] == AIM_BONUS
    assert order_event.cause.summary_key.endswith("_aim")


def test_aim_persists_to_the_next_turn_without_a_new_aim_event() -> None:
    first = plan_ai_orders(_world(), SCENARIO)
    world = first.world
    world.accepted_commands = []
    world.clock.turn += 1

    second = plan_ai_orders(world, SCENARIO)

    assert second.world.aims[CAUTIOUS_RIVAL] == first.world.aims[CAUTIOUS_RIVAL]
    assert [e for e in second.events if e.kind == "ai_aim_set"] == []


def test_ruleset_one_world_has_no_aims() -> None:
    world = _world()
    world.ai_ruleset = 1

    plan = plan_ai_orders(world, SCENARIO)

    assert plan.world.aims == {}
    assert "ai_aim_set" not in [event.kind for event in plan.events]
    assert all(event.cause.inputs.get("aim_score", 0) == 0 for event in plan.events)


def test_without_a_stance_the_aim_decides_the_tax_direction() -> None:
    plan = plan_ai_orders(_world(stance=None), SCENARIO)

    aim = plan.world.aims[CAUTIOUS_RIVAL]
    commands = [
        c for c in plan.world.accepted_commands if c.faction_id == CAUTIOUS_RIVAL
    ]
    expected = {ScoreCategory.HOARD: TaxRate.HIGH, ScoreCategory.BUILD: TaxRate.LOW}
    if aim.category in expected:
        assert [c.command.tax_rate for c in commands] == [expected[aim.category]]
    else:
        assert commands == []


def test_orders_aimed_at_the_aim_target_get_a_bonus() -> None:
    from app.models.orders import CallNegotiationOrder

    world = _world()
    aim = _hoard_aim(world).model_copy(update={"target_faction_id": WRATHFUL_RIVAL})
    world.aims[CAUTIOUS_RIVAL] = aim
    talk = Candidate(
        CallNegotiationOrder(
            faction_id=CAUTIOUS_RIVAL, target_faction_id=WRATHFUL_RIVAL
        ),
        ScoreCategory.ALLY,
    )
    other = Candidate(
        CallNegotiationOrder(faction_id=CAUTIOUS_RIVAL, target_faction_id="house_x"),
        ScoreCategory.ALLY,
    )

    on_target = score_candidate(world, SCENARIO, CAUTIOUS_RIVAL, talk)
    off_target = score_candidate(world, SCENARIO, CAUTIOUS_RIVAL, other)

    assert on_target.aim_score == SCENARIO.tuning.ai.aim_target_bonus
    assert off_target.aim_score == 0
