import pytest
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.diplomacy.prisoners import handle_prisoner, ransom_price
from app.engine.diplomacy.validation import validate_prisoner_order
from app.engine.peace.hostages import hold_hostage
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import CommandStatus
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState, TruceState
from strategy_contracts.enums import TroopType
from strategy_contracts.terms import HostageTerm

from tests.engine.diplomacy.builders import queue_npc_order, run_phase
from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.peace
EAGER_SCENARIO = SCENARIO.model_copy(
    update={
        "tuning": SCENARIO.tuning.model_copy(
            update={"peace": TUNING.model_copy(update={"ransom_base_percent": 200})}
        )
    }
)


def _troops(
    world, holder: str, origin: str, prisoner_id: str = "prisoner_1", count: int = 10
) -> PrisonerState:
    prisoner = PrisonerState(
        id=prisoner_id,
        held_by_id=holder,
        origin_faction_id=origin,
        kind=PrisonerKind.TROOPS,
        troop_count=count,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: count},
    )
    world.prisoners.append(prisoner)
    return prisoner


def _order(prisoner_id: str, action: str, holder: str = PLAYER) -> HandlePrisonerOrder:
    return HandlePrisonerOrder(
        faction_id=holder, prisoner_id=prisoner_id, action=action
    )


def test_ransom_price_scales_with_troops() -> None:
    world = make_world()
    prisoner = _troops(world, PLAYER, WRATHFUL_RIVAL, count=10)

    assert ransom_price(prisoner, TUNING) == 10 * TUNING.ransom_gold_per_troop


def test_ransom_moves_gold_frees_prisoner_and_scores_a_chip() -> None:
    world = make_world()
    war = add_war(world)
    prisoner = _troops(world, PLAYER, WRATHFUL_RIVAL)
    price = ransom_price(prisoner, TUNING)
    payer_before = world.factions[WRATHFUL_RIVAL].treasury
    holder_before = world.factions[PLAYER].treasury

    handle_prisoner(world, EAGER_SCENARIO, _order("prisoner_1", "ransom"))

    assert world.prisoners == []
    assert world.factions[WRATHFUL_RIVAL].treasury == payer_before - price
    assert world.factions[PLAYER].treasury == holder_before + price
    key = f"{war.id}:{PLAYER}"
    assert world.peace.ransom_points[key] == TUNING.ransom_score_chip


def test_legacy_ransom_fails_when_origin_cannot_pay() -> None:
    world = make_world()
    world.peace_ruleset = 1
    add_war(world)
    _troops(world, PLAYER, WRATHFUL_RIVAL)
    world.factions[WRATHFUL_RIVAL].treasury = 0

    with pytest.raises(CommandError) as error:
        validate_prisoner_order(world, SCENARIO, _order("prisoner_1", "ransom"))

    assert error.value.code == "cannot_pay"


def test_exchange_is_symmetric() -> None:
    world = make_world()
    war = add_war(world)
    _troops(world, PLAYER, WRATHFUL_RIVAL, "prisoner_1", 10)
    _troops(world, WRATHFUL_RIVAL, PLAYER, "prisoner_2", 10)

    handle_prisoner(world, SCENARIO, _order("prisoner_1", "exchange"))

    assert world.prisoners == []
    chip = TUNING.exchange_score_chip
    assert world.peace.ransom_points[f"{war.id}:{PLAYER}"] == chip
    assert world.peace.ransom_points[f"{war.id}:{WRATHFUL_RIVAL}"] == chip


def test_exchange_without_counterpart_is_rejected() -> None:
    world = make_world()
    add_war(world)
    _troops(world, PLAYER, WRATHFUL_RIVAL)

    with pytest.raises(CommandError) as error:
        validate_prisoner_order(world, SCENARIO, _order("prisoner_1", "exchange"))

    assert error.value.code == "no_exchange_counterpart"


def test_release_frees_the_prisoner_without_score() -> None:
    world = make_world()
    war = add_war(world)
    _troops(world, PLAYER, WRATHFUL_RIVAL)

    handle_prisoner(world, SCENARIO, _order("prisoner_1", "release"))

    assert world.prisoners == []
    assert f"{war.id}:{PLAYER}" not in world.peace.ransom_points


def test_execute_applies_an_atrocity() -> None:
    world = make_world()
    add_war(world)
    _troops(world, PLAYER, WRATHFUL_RIVAL)
    before = world.factions[PLAYER].reputation

    events = handle_prisoner(world, SCENARIO, _order("prisoner_1", "execute"))

    assert world.prisoners == []
    assert world.factions[PLAYER].reputation == before - TUNING.atrocity_reputation_cost
    assert [event.kind for event in events] == ["prisoner_executed"]


def test_not_holder_is_rejected() -> None:
    world = make_world()
    _troops(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    with pytest.raises(CommandError) as error:
        validate_prisoner_order(world, SCENARIO, _order("prisoner_1", "release"))

    assert error.value.code == "not_holder"


def test_unknown_prisoner_is_rejected() -> None:
    world = make_world()

    with pytest.raises(CommandError) as error:
        validate_prisoner_order(world, SCENARIO, _order("prisoner_9", "release"))

    assert error.value.code == "unknown_prisoner"


def test_order_for_a_prisoner_freed_meanwhile_fails_and_refunds() -> None:
    world = make_world()
    _troops(world, PLAYER, WRATHFUL_RIVAL)
    world = queue_npc_order(world, SCENARIO, _order("prisoner_1", "release"))
    world.prisoners = []
    command = world.accepted_commands[-1]
    before = world.factions[PLAYER].orders_remaining

    result = run_phase(DiplomacyPhase(), world)

    failed = result.world.accepted_commands[-1]
    assert failed.status == CommandStatus.FAILED
    assert (
        result.world.factions[PLAYER].orders_remaining == before + command.reserved_cost
    )


def _hostage(world):
    first, second = sorted((PLAYER, WRATHFUL_RIVAL))
    world.truces.append(TruceState(id="truce_1", faction_a=first, faction_b=second))
    term = HostageTerm(
        giver_id=WRATHFUL_RIVAL,
        holder_id=PLAYER,
        leader_id=world.factions[WRATHFUL_RIVAL].leader_id,
        duration_turns=5,
    )
    return hold_hostage(world, term, "truce_1")


def test_executing_a_hostage_is_routed_to_harm() -> None:
    world = make_world()
    hostage = _hostage(world)

    events = handle_prisoner(world, SCENARIO, _order(hostage.id, "execute"))

    assert world.peace.hostages == []
    assert "hostage_harmed" in [event.kind for event in events]


def test_releasing_a_hostage_sends_them_home() -> None:
    world = make_world()
    hostage = _hostage(world)

    events = handle_prisoner(world, SCENARIO, _order(hostage.id, "release"))

    assert world.peace.hostages == []
    assert [event.kind for event in events] == ["hostage_released"]


def test_ransoming_a_hostage_is_rejected() -> None:
    world = make_world()
    hostage = _hostage(world)

    with pytest.raises(CommandError) as error:
        validate_prisoner_order(world, SCENARIO, _order(hostage.id, "ransom"))

    assert error.value.code == "invalid_hostage_action"
