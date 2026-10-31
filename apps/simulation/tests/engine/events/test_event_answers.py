from uuid import NAMESPACE_URL, uuid5

import pytest
from app.engine.campaign import begin_campaign
from app.engine.commands.application import accept_command
from app.engine.commands.cancellation import cancel_command
from app.engine.commands.check import check_command
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.exceptions.command_exceptions import CommandError
from app.models.api_orders import OrderFlag
from app.models.battle_command import CommandStatus
from app.models.battle_progress import OperationGuard
from app.models.orders import AnswerEventOrder
from app.models.replay import (
    AcceptCommandReplayInput,
    BeginCampaignReplayInput,
    ReplayStep,
    ReplayStepKind,
)
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns
from tests.models.builders import PLAYTHROUGH_ID, make_world

PLAYER = "house_carrow"
HOME = "carrow_vale"
ACTOR = "player-user"
HIGH_UNREST = 70
EASE_COST = 1
CRACKDOWN_COST = 2
EASE_GOLD = 20
EASE_UNREST_RELIEF = 10
EASE_SCAR = 5
STARTING_ORDERS = 6


def _scenario():
    scenario = load_three_crowns()
    scenario.tuning.event_frequency_percent = 100
    return scenario


def _fresh_world() -> WorldState:
    world = make_world()
    world.events_ruleset = 1
    world.regions[HOME].unrest = HIGH_UNREST
    return world


def _fired_world() -> WorldState:
    return begin_campaign(_fresh_world(), _scenario()).world


def _grievance_id(world: WorldState) -> str:
    return next(
        pending.id
        for pending in world.pending_events
        if pending.template_id == "tax_grievance"
    )


def _answer(world: WorldState, choice_id: str = "ease_taxes") -> AnswerEventOrder:
    return AnswerEventOrder(
        faction_id=PLAYER, event_id=_grievance_id(world), choice_id=choice_id
    )


def _accept(world: WorldState, order: AnswerEventOrder, operation: str = "op-1"):
    identity = str(uuid5(NAMESPACE_URL, f"{world.playthrough_id}:{ACTOR}:{operation}"))
    return accept_command(
        world,
        _scenario(),
        order,
        command_id=identity,
        operation_id=operation,
        actor_id=ACTOR,
        faction_id=PLAYER,
        expected_turn=world.clock.turn,
        expected_wave=0,
    )


def test_answering_spends_the_choices_order_cost() -> None:
    world = _fired_world()
    before = world.factions[PLAYER].orders_remaining
    accepted = _accept(world, _answer(world))
    assert accepted.world.factions[PLAYER].orders_remaining == before - EASE_COST
    assert accepted.command is not None
    assert accepted.command.reserved_cost == EASE_COST
    assert accepted.command.status is CommandStatus.ACCEPTED


def test_a_costlier_choice_spends_more() -> None:
    world = _fired_world()
    before = world.factions[PLAYER].orders_remaining
    accepted = _accept(world, _answer(world, "garrison_crackdown"))
    assert accepted.world.factions[PLAYER].orders_remaining == before - CRACKDOWN_COST


def test_the_answer_takes_effect_in_the_next_resolution() -> None:
    world = _fired_world()
    event_id = _grievance_id(world)
    treasury = world.factions[PLAYER].treasury
    queued = _accept(world, _answer(world)).world
    assert any(pending.id == event_id for pending in queued.pending_events)
    result = begin_campaign(queued, _scenario())
    after = result.world
    assert all(pending.id != event_id for pending in after.pending_events)
    assert after.factions[PLAYER].treasury < treasury
    answered = [e for e in result.events if e.kind == "event_answered"]
    assert answered
    assert answered[0].cause.summary_key == "events.tax_grievance.ease_taxes"
    memory = next(m for m in after.event_memories if m.template_id == "tax_grievance")
    assert memory.scar >= EASE_SCAR


def test_cancelling_refunds_the_order_points() -> None:
    world = _fired_world()
    accepted = _accept(world, _answer(world))
    assert accepted.command is not None
    cancelled = cancel_command(
        accepted.world,
        _scenario(),
        accepted.command.id,
        faction_id=PLAYER,
        expected_turn=world.clock.turn,
    )
    assert cancelled.factions[PLAYER].orders_remaining == (
        world.factions[PLAYER].orders_remaining
    )
    assert cancelled.accepted_commands == []


def test_answer_beyond_the_remaining_orders_is_refused() -> None:
    world = _fired_world()
    world.factions[PLAYER].orders_remaining = EASE_COST - 1
    with pytest.raises(CommandError) as error:
        _accept(world, _answer(world))
    assert error.value.code == "insufficient_points"


def test_answer_the_treasury_cannot_pay_is_refused() -> None:
    world = _fired_world()
    world.factions[PLAYER].treasury = EASE_GOLD - 1
    with pytest.raises(CommandError) as error:
        _accept(world, _answer(world))
    assert error.value.code == "insufficient_funds"


def test_two_queued_answers_cannot_overspend_the_treasury_together() -> None:
    world = _fired_world()
    other = world.pending_events[0].model_copy(
        update={"id": "event_99", "subject_id": "elsewhere"}
    )
    world.pending_events.append(other)
    world.factions[PLAYER].treasury = EASE_GOLD + EASE_GOLD - 1
    first = _accept(world, _answer(world), "op-1").world
    second = AnswerEventOrder(
        faction_id=PLAYER, event_id="event_99", choice_id="ease_taxes"
    )
    with pytest.raises(CommandError) as error:
        _accept(first, second, "op-2")
    assert error.value.code == "insufficient_funds"


def test_one_event_can_be_answered_once() -> None:
    world = _fired_world()
    first = _accept(world, _answer(world), "op-1").world
    with pytest.raises(CommandError) as error:
        _accept(first, _answer(world, "garrison_crackdown"), "op-2")
    assert error.value.code == "duplicate_slot"


def test_unknown_event_and_unoffered_choice_are_refused() -> None:
    world = _fired_world()
    missing = AnswerEventOrder(
        faction_id=PLAYER, event_id="event_404", choice_id="nothing"
    )
    with pytest.raises(CommandError) as not_found:
        _accept(world, missing)
    assert not_found.value.code == "not_found"
    with pytest.raises(CommandError) as bad_choice:
        _accept(world, _answer(world, "pay_arrears"))
    assert bad_choice.value.code == "invalid_choice"


def test_check_flags_an_unaffordable_answer_without_charging() -> None:
    world = _fired_world()
    world.factions[PLAYER].orders_remaining = 0
    check = check_command(
        world,
        _scenario(),
        _answer(world),
        faction_id=PLAYER,
        expected_turn=world.clock.turn,
        expected_wave=0,
    )
    assert check.flag is OrderFlag.OVER_BUDGET
    assert world.factions[PLAYER].orders_remaining == 0


def test_an_unanswered_event_is_neglected_at_the_next_resolution() -> None:
    world = _fired_world()
    event_id = _grievance_id(world)
    result = begin_campaign(world, _scenario())
    assert all(pending.id != event_id for pending in result.world.pending_events)
    assert any(event.kind == "event_neglected" for event in result.events)


def _guard(operation: str, turn: int) -> OperationGuard:
    return OperationGuard(
        operation_id=operation,
        expected_world_version=1,
        expected_turn=turn,
        expected_wave=0,
    )


def _step(
    sequence: int,
    kind: ReplayStepKind,
    replay_input: BeginCampaignReplayInput | AcceptCommandReplayInput,
    before: WorldState,
    after: WorldState,
) -> ReplayStep:
    return ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=sequence,
        operation_id=replay_input.guard.operation_id,
        kind=kind,
        input=replay_input,
        before_hash=world_hash(before),
        after_hash=world_hash(after),
        turn=before.clock.turn,
        wave=0,
    )


def test_replay_reproduces_a_turn_with_an_answered_event() -> None:
    start = _fresh_world()
    fired = begin_campaign(start.model_copy(deep=True), _scenario()).world
    order = _answer(fired)
    queued = _accept(fired, order).world
    resolved = begin_campaign(queued.model_copy(deep=True), _scenario()).world
    steps = [
        _step(
            1,
            ReplayStepKind.BEGIN_CAMPAIGN,
            BeginCampaignReplayInput(guard=_guard("begin-1", 0)),
            start,
            fired,
        ),
        _step(
            2,
            ReplayStepKind.ACCEPT_COMMAND,
            AcceptCommandReplayInput(
                actor_id=ACTOR, guard=_guard("op-1", 1), command=order
            ),
            fired,
            queued,
        ),
        _step(
            3,
            ReplayStepKind.BEGIN_CAMPAIGN,
            BeginCampaignReplayInput(guard=_guard("begin-2", 1)),
            queued,
            resolved,
        ),
    ]
    result = replay_history(start, _scenario(), steps)
    assert result.world_hash == world_hash(resolved)
