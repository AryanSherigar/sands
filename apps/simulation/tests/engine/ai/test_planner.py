from app.engine.ai import planner
from app.engine.ai.candidates import Candidate, ScoredCandidate
from app.engine.ai.planner import plan_ai_orders
from app.engine.hashing import world_hash
from app.models.orders import SetPayOrder
from app.models.world_events import PhaseName
from app.models.world_state import CounterKind
from strategy_contracts.enums import PayLevel, TaxRate
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

LAYER_ONE_RULESET = 1
TAX_ORDER_COST = SCENARIO.tuning.order_costs["set_tax_rate"]


def _world_with_stance(stance_id: str | None):
    world = make_world()
    world.ai_ruleset = LAYER_ONE_RULESET
    world.factions[CAUTIOUS_RIVAL].stance.option_id = stance_id
    world.factions[WRATHFUL_RIVAL].leader_id = None
    return world


def _commands(plan, faction_id: str):
    return [
        item for item in plan.world.accepted_commands if item.faction_id == faction_id
    ]


def test_player_faction_gets_no_ai_orders() -> None:
    plan = plan_ai_orders(_world_with_stance("turtle"), SCENARIO)

    assert _commands(plan, PLAYER) == []


def test_destroyed_and_leaderless_factions_get_no_orders() -> None:
    world = _world_with_stance("turtle")
    world.factions[CAUTIOUS_RIVAL].is_destroyed = True

    plan = plan_ai_orders(world, SCENARIO)

    assert plan.world.accepted_commands == []
    assert plan.events == []


def test_ai_orders_are_recorded_under_npc_actor_and_cost_budget() -> None:
    world = _world_with_stance("turtle")
    before = world.factions[CAUTIOUS_RIVAL].orders_remaining

    plan = plan_ai_orders(world, SCENARIO)

    commands = _commands(plan, CAUTIOUS_RIVAL)
    assert [item.actor_id for item in commands] == [f"npc:{CAUTIOUS_RIVAL}"]
    spent = sum(item.reserved_cost for item in commands)
    assert plan.world.factions[CAUTIOUS_RIVAL].orders_remaining == before - spent


def test_stance_hoard_vs_build_changes_tax_direction() -> None:
    hoarding = plan_ai_orders(_world_with_stance("turtle"), SCENARIO)
    building = plan_ai_orders(_world_with_stance("rebuild"), SCENARIO)

    assert _commands(hoarding, CAUTIOUS_RIVAL)[0].command.tax_rate == TaxRate.HIGH
    assert _commands(building, CAUTIOUS_RIVAL)[0].command.tax_rate == TaxRate.LOW


def test_balanced_ruler_without_stance_keeps_the_status_quo() -> None:
    plan = plan_ai_orders(_world_with_stance(None), SCENARIO)

    assert plan.world.accepted_commands == []


def test_planner_does_not_mutate_input_world() -> None:
    world = _world_with_stance("turtle")
    before = world_hash(world)

    plan_ai_orders(world, SCENARIO)

    assert world_hash(world) == before


def test_each_planned_order_has_one_hidden_reason_event() -> None:
    world = _world_with_stance("turtle")
    start_seq = world.counters.get(CounterKind.EVENT_SEQ, 0)

    plan = plan_ai_orders(world, SCENARIO)

    commands = _commands(plan, CAUTIOUS_RIVAL)
    assert len(plan.events) == len(commands) == 1
    event = plan.events[0]
    assert (event.kind, event.phase) == ("ai_order_planned", PhaseName.ORDERS)
    assert event.seq == start_seq + 1
    assert event.cause.subject_ids == [CAUTIOUS_RIVAL]
    assert set(event.cause.inputs) == {
        "score",
        "trait_score",
        "stance_score",
        "aim_score",
        "adjustment",
    }
    assert plan.world.counters[CounterKind.EVENT_SEQ] == start_seq + 1


def test_planning_is_deterministic_for_same_world_and_seed() -> None:
    first = plan_ai_orders(_world_with_stance("turtle"), SCENARIO)
    second = plan_ai_orders(_world_with_stance("turtle"), SCENARIO)

    assert world_hash(first.world) == world_hash(second.world)
    assert first.events == second.events


def test_zero_budget_faction_queues_nothing() -> None:
    world = _world_with_stance("turtle")
    world.factions[CAUTIOUS_RIVAL].orders_remaining = 0

    plan = plan_ai_orders(world, SCENARIO)

    assert plan.world.accepted_commands == []


def test_an_order_the_validator_rejects_is_logged_not_queued(monkeypatch) -> None:
    ghost = SetPayOrder(
        faction_id=CAUTIOUS_RIVAL, army_id="ghost", pay_level=PayLevel.FULL
    )
    pick = ScoredCandidate(Candidate(ghost, ScoreCategory.BUILD), 10, 10, 0)
    monkeypatch.setattr(planner, "select_orders", lambda *_, **__: [pick])
    world = _world_with_stance("turtle")
    before = world.factions[CAUTIOUS_RIVAL].orders_remaining

    plan = plan_ai_orders(world, SCENARIO)

    assert plan.world.accepted_commands == []
    assert [event.kind for event in plan.events] == ["ai_order_rejected"]
    assert plan.world.factions[CAUTIOUS_RIVAL].orders_remaining == before


def test_events_returned_by_accepted_commands_are_kept() -> None:
    from app.models.world_internal import UprisingState

    world = _world_with_stance("turtle")
    world.ai_ruleset = 2
    world.internal_ruleset = 1
    world.uprisings.append(
        UprisingState(
            id="up_1",
            region_id="carrow_vale",
            faction_id=CAUTIOUS_RIVAL,
            started_turn=0,
            trigger_unrest=80,
            income_penalty_percent=10,
            manpower_penalty_percent=10,
            supply_penalty_percent=10,
        )
    )

    plan = plan_ai_orders(world, SCENARIO)

    assert plan.world.uprisings == []
    kinds = [event.kind for event in plan.events]
    assert "uprising_resolved" in kinds
    seqs = [event.seq for event in plan.events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
