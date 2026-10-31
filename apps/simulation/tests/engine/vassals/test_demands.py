import pytest
from app.engine.vassals.commands import apply_vassal_order, validate_vassal_order
from app.engine.vassals.demands import resolve_demands
from app.exceptions.command_exceptions import CommandError
from app.models.orders import AnswerDemandOrder, DemandFromVassalOrder
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_vassal import VassalStanding
from app.services.world_projection import project_world
from strategy_contracts.vassal import DemandKind, DemandReply

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_world,
    set_axes,
    set_power,
    set_unrest,
)

TUNING = SCENARIO.tuning.vassal
FORBIDDEN_KEYS = {"grievance", "standing", "temperament", "strength", "reply_scores"}


def _demand_order(vassalage_id: str, amount: int = 60, faction: str = PLAYER):
    return DemandFromVassalOrder(
        faction_id=faction,
        vassalage_id=vassalage_id,
        demand_kind=DemandKind.TRIBUTE,
        amount=amount,
    )


def _reason(order, world) -> str:
    with pytest.raises(CommandError) as refused:
        validate_vassal_order(world, SCENARIO, order)
    return refused.value.code


def _issue(world, order):
    validate_vassal_order(world, SCENARIO, order)
    return apply_vassal_order(world, SCENARIO, order)


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def test_unknown_vassalage_is_rejected() -> None:
    assert _reason(_demand_order("commitment_9"), make_world()) == "unknown_vassalage"


def test_non_overlord_demand_is_rejected() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)

    assert _reason(_demand_order(commitment.id, faction=WRATHFUL_RIVAL), world) == (
        "not_overlord"
    )


def test_covered_demand_is_rejected_as_no_excess() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=30)

    assert _reason(_demand_order(commitment.id, amount=30), world) == "no_excess"


def test_second_demand_while_one_is_pending_is_rejected() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    _issue(world, _demand_order(commitment.id))

    assert _reason(_demand_order(commitment.id), world) == "demand_pending"


def test_demand_inside_the_cooldown_is_rejected() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    _issue(world, _demand_order(commitment.id))
    world.vassal.demands.clear()

    assert _reason(_demand_order(commitment.id), world) == "demand_cooldown"
    world.clock.turn += TUNING.demand_cooldown_turns
    validate_vassal_order(world, SCENARIO, _demand_order(commitment.id))


def test_issue_demand_raises_unrest_immediately() -> None:
    world = make_world()
    set_unrest(world, CAUTIOUS_RIVAL, 10)
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)

    _issue(world, _demand_order(commitment.id))

    assert all(
        region.unrest > 10
        for region in world.regions.values()
        if region.owner_id == CAUTIOUS_RIVAL
    )
    [demand] = world.vassal.demands
    assert demand.deadline_turn == world.clock.turn + TUNING.demand_answer_turns


def test_npc_vassal_answers_at_the_deadline_with_a_named_reason() -> None:
    world = make_world()
    scenario = set_axes(world, SCENARIO, CAUTIOUS_RIVAL, honor=3, trust=3)
    set_power(world, CAUTIOUS_RIVAL, PLAYER, 300, 1000)
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    _issue(world, _demand_order(commitment.id, amount=30))
    world.clock.turn += TUNING.demand_answer_turns

    events = resolve_demands(world, scenario)

    assert world.vassal.demands == []
    [answered] = [e for e in events if e.kind == "demand_answered"]
    assert answered.cause.summary_key.startswith("demand_answered_accept_")


def test_player_vassal_sees_pending_demand_and_answers_with_each_reply() -> None:
    for reply in DemandReply:
        world = make_world()
        commitment = add_vassalage(world, WRATHFUL_RIVAL, PLAYER)
        _issue(world, _demand_order(commitment.id, faction=WRATHFUL_RIVAL))
        view = project_world(world, SCENARIO, 1, "digest").model_dump(mode="json")
        assert [item["kind"] for item in view["pending_demands"]] == ["tribute"]
        [demand] = world.vassal.demands

        answer = AnswerDemandOrder(faction_id=PLAYER, demand_id=demand.id, reply=reply)
        _issue(world, answer)

        assert world.vassal.demands == []


def test_unanswered_player_vassal_demand_is_a_refusal() -> None:
    world = make_world()
    commitment = add_vassalage(world, WRATHFUL_RIVAL, PLAYER)
    _issue(world, _demand_order(commitment.id, faction=WRATHFUL_RIVAL))
    world.clock.turn += TUNING.demand_answer_turns

    events = resolve_demands(world, SCENARIO)

    assert any(
        e.cause.summary_key.startswith("demand_answered_refuse_") for e in events
    )
    assert world.vassal.standing[0].grievance == TUNING.refuse_grievance


def test_demand_answered_twice_is_rejected() -> None:
    world = make_world()
    commitment = add_vassalage(world, WRATHFUL_RIVAL, PLAYER)
    _issue(world, _demand_order(commitment.id, faction=WRATHFUL_RIVAL))
    [demand] = world.vassal.demands
    answer = AnswerDemandOrder(
        faction_id=PLAYER, demand_id=demand.id, reply=DemandReply.REFUSE
    )
    _issue(world, answer)

    assert _reason(answer, world) == "unknown_demand"


def test_answer_by_a_non_vassal_or_after_the_deadline_is_rejected() -> None:
    world = make_world()
    commitment = add_vassalage(world, WRATHFUL_RIVAL, PLAYER)
    _issue(world, _demand_order(commitment.id, faction=WRATHFUL_RIVAL))
    [demand] = world.vassal.demands
    stranger = AnswerDemandOrder(
        faction_id=CAUTIOUS_RIVAL, demand_id=demand.id, reply=DemandReply.ACCEPT
    )
    late = AnswerDemandOrder(
        faction_id=PLAYER, demand_id=demand.id, reply=DemandReply.ACCEPT
    )

    assert _reason(stranger, world) == "not_vassal"
    world.clock.turn = demand.deadline_turn + 1
    assert _reason(late, world) == "demand_expired"


def test_view_hides_npc_scores_and_grievance() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    _issue(world, _demand_order(commitment.id))
    world.vassal.standing.append(
        VassalStanding(vassalage_id=commitment.id, grievance=5)
    )

    view = project_world(world, SCENARIO, 1, "digest").model_dump(mode="json")

    assert not FORBIDDEN_KEYS & _keys(view)
    assert view["vassalages"][0]["vassal_id"] == CAUTIOUS_RIVAL
    assert view["pending_demands"] == []


def test_answer_after_the_vassalage_ended_is_rejected() -> None:
    world = make_world()
    commitment = add_vassalage(world, WRATHFUL_RIVAL, PLAYER)
    _issue(world, _demand_order(commitment.id, faction=WRATHFUL_RIVAL))
    [demand] = world.vassal.demands
    commitment.status = CommitmentStatus.EXPIRED
    answer = AnswerDemandOrder(
        faction_id=PLAYER, demand_id=demand.id, reply=DemandReply.ACCEPT
    )

    assert _reason(answer, world) == "unknown_vassalage"


def test_leaderless_npc_vassal_refuses_instead_of_crashing() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    _issue(world, _demand_order(commitment.id))
    world.factions[CAUTIOUS_RIVAL].leader_id = None
    world.clock.turn += TUNING.demand_answer_turns

    events = resolve_demands(world, SCENARIO)

    assert world.vassal.demands == []
    assert any(
        e.cause.summary_key.startswith("demand_answered_refuse_") for e in events
    )
