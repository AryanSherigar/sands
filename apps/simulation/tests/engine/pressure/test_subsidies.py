import pytest
from app.engine.diplomacy.phase import DiplomacyPhase, TimePhase
from app.engine.pressure.hope import derive_hope
from app.engine.pressure.subsidies import (
    pay_subsidies,
    validate_cut_subsidy,
    validate_subsidize,
)
from app.engine.pressure.will import compute_will
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import CommandStatus
from app.models.orders import CutSubsidyOrder, SubsidizeOrder
from app.models.world_diplomacy import WarSide
from app.models.world_pressure import SubsidyState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.pressure import HopeSource

from tests.engine.diplomacy.builders import queue_npc_order, run_phase
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.pressure
PAYER = CAUTIOUS_RIVAL
RECEIVER = WRATHFUL_RIVAL
RICH = 1000


def _war_world(treasury: int = RICH):
    world = make_world()
    war = add_war(world, attacker_id=RECEIVER, defender_id=PLAYER)
    world.factions[PAYER].treasury = treasury
    return world, war


def _grant(
    war_id: str = "war_1",
    amount: int = 10,
    turns: int = 3,
    payer: str = PAYER,
    receiver: str = RECEIVER,
) -> SubsidizeOrder:
    return SubsidizeOrder(
        faction_id=payer,
        target_faction_id=receiver,
        war_id=war_id,
        amount_per_turn=amount,
        turns=turns,
    )


def _resolve(world, order):
    world = queue_npc_order(world, SCENARIO, order)
    budget = world.factions[order.faction_id].orders_remaining
    result = run_phase(DiplomacyPhase(), world)
    return result.world, budget, result.events


def _subsidized_world(amount: int = 10, turns: int = 3):
    world, _ = _war_world()
    resolved, _, _ = _resolve(world, _grant(amount=amount, turns=turns))
    return resolved


def test_subsidize_creates_a_subsidy_and_costs_one_order() -> None:
    world, _ = _war_world()
    start = world.factions[PAYER].orders_remaining

    resolved, budget, events = _resolve(world, _grant())

    subsidy = resolved.pressure.subsidies[0]
    assert (subsidy.payer_id, subsidy.receiver_id) == (PAYER, RECEIVER)
    assert subsidy.amount_per_turn == 10
    assert subsidy.expires_turn == world.clock.turn + 2
    assert start - resolved.factions[PAYER].orders_remaining == 1
    assert budget == start - 1
    assert "subsidy_granted" in [event.kind for event in events]


@pytest.mark.parametrize(
    ("reason", "order"),
    [
        ("unknown_war", _grant(war_id="war_9")),
        ("receiver_unavailable", _grant(receiver=PAYER)),
        ("receiver_not_in_war", _grant(payer=RECEIVER, receiver=PAYER)),
        ("payer_is_enemy", _grant(payer=RECEIVER, receiver=PLAYER)),
        ("bad_amount", _grant(amount=0)),
        ("bad_amount", _grant(amount=TUNING.subsidy_max_per_turn + 1)),
        ("bad_duration", _grant(turns=0)),
        ("bad_duration", _grant(turns=TUNING.subsidy_max_turns + 1)),
        ("cannot_pay", _grant(amount=50)),
    ],
)
def test_invalid_subsidies_are_rejected_when_queued(reason, order) -> None:
    world, _ = _war_world(treasury=49)

    with pytest.raises(CommandError) as error:
        validate_subsidize(world, SCENARIO, order)

    assert error.value.code == reason


def test_a_payer_at_war_with_the_receiver_elsewhere_is_an_enemy() -> None:
    world, _ = _war_world()
    pair = tuple(sorted((PAYER, RECEIVER)))
    relation = next(
        item for item in world.relations if (item.faction_a, item.faction_b) == pair
    )
    relation.status = RelationStatus.WAR

    with pytest.raises(CommandError) as error:
        validate_subsidize(world, SCENARIO, _grant())

    assert error.value.code == "payer_is_enemy"


def test_a_subsidy_for_the_same_war_and_pair_is_rejected() -> None:
    world = _subsidized_world()

    with pytest.raises(CommandError) as error:
        validate_subsidize(world, SCENARIO, _grant())

    assert error.value.code == "subsidy_exists"


def test_subsidize_is_rejected_when_pressure_is_disabled() -> None:
    world, _ = _war_world()
    world.pressure_ruleset = 0

    with pytest.raises(CommandError) as error:
        validate_subsidize(world, SCENARIO, _grant())

    assert error.value.code == "pressure_disabled"


def _drop_war(world) -> None:
    world.wars = []


def _destroy_receiver(world) -> None:
    world.factions[RECEIVER].is_destroyed = True


def _swap_attacker(world) -> None:
    world.wars[0].attacker_id = PAYER


def _enlist_payer_against_receiver(world) -> None:
    world.wars[0].side_by_faction[PAYER] = WarSide.DEFENDER


def _impoverish_payer(world) -> None:
    world.factions[PAYER].treasury = 0


def _duplicate_subsidy(world) -> None:
    world.pressure.subsidies.append(
        SubsidyState(
            id="subsidy_9",
            payer_id=PAYER,
            receiver_id=RECEIVER,
            war_id="war_1",
            expires_turn=world.clock.turn + 5,
            amount_per_turn=5,
        )
    )


def _disable_pressure(world) -> None:
    world.pressure_ruleset = 0


@pytest.mark.parametrize(
    ("reason", "sabotage"),
    [
        ("unknown_war", _drop_war),
        ("receiver_unavailable", _destroy_receiver),
        ("receiver_not_in_war", _swap_attacker),
        ("payer_is_enemy", _enlist_payer_against_receiver),
        ("cannot_pay", _impoverish_payer),
        ("subsidy_exists", _duplicate_subsidy),
        ("pressure_disabled", _disable_pressure),
    ],
)
def test_order_that_goes_stale_before_resolving_fails_and_is_refunded(
    reason, sabotage
) -> None:
    world, _ = _war_world()
    world = queue_npc_order(world, SCENARIO, _grant())
    budget = world.factions[PAYER].orders_remaining
    sabotage(world)

    result = run_phase(DiplomacyPhase(), world)

    command = result.world.accepted_commands[-1]
    assert command.status == CommandStatus.FAILED
    assert command.failure_reason == reason
    assert result.world.factions[PAYER].orders_remaining == budget + 1
    assert [s.id for s in result.world.pressure.subsidies] == (
        ["subsidy_9"] if reason == "subsidy_exists" else []
    )


def test_instalment_moves_gold_each_turn_and_stops_after_the_last_turn() -> None:
    world = _subsidized_world(amount=10, turns=3)
    payer_before = world.factions[PAYER].treasury
    receiver_before = world.factions[RECEIVER].treasury

    for _ in range(5):
        world = run_phase(TimePhase(), world).world
        world.clock.turn += 1

    assert payer_before - world.factions[PAYER].treasury == 30
    assert world.factions[RECEIVER].treasury - receiver_before == 30
    assert world.pressure.subsidies == []


def test_payer_that_cannot_pay_defaults_and_loses_the_subsidy() -> None:
    world = _subsidized_world(amount=10, turns=3)
    world.factions[PAYER].treasury = 9

    events = pay_subsidies(world)

    assert world.pressure.subsidies == []
    assert world.factions[PAYER].treasury == 9
    assert [event.kind for event in events] == ["subsidy_defaulted"]


def test_cutting_removes_it_and_the_receivers_will_and_hope_drop_that_turn() -> None:
    world = _subsidized_world()
    war = world.wars[0]
    subsidy_id = world.pressure.subsidies[0].id
    factors_before = compute_will(world, SCENARIO, RECEIVER).factors
    hope_before = derive_hope(world, SCENARIO, RECEIVER, war).sources

    cut, _, events = _resolve(
        world, CutSubsidyOrder(faction_id=PAYER, subsidy_id=subsidy_id)
    )

    assert cut.pressure.subsidies == []
    assert HopeSource.SUBSIDY in hope_before
    assert HopeSource.SUBSIDY not in derive_hope(cut, SCENARIO, RECEIVER, war).sources
    factors_after = compute_will(cut, SCENARIO, RECEIVER).factors
    assert factors_before["subsidy"] > factors_after["subsidy"] == 0
    assert "subsidy_cut" in [event.kind for event in events]


def test_cutting_someone_elses_subsidy_is_rejected() -> None:
    world = _subsidized_world()

    with pytest.raises(CommandError) as error:
        validate_cut_subsidy(
            world, CutSubsidyOrder(faction_id=PLAYER, subsidy_id="subsidy_1")
        )

    assert error.value.code == "not_payer"
    assert len(world.pressure.subsidies) == 1


def test_a_second_cut_in_the_same_turn_is_a_duplicate_slot() -> None:
    world = _subsidized_world()
    cut = CutSubsidyOrder(faction_id=PAYER, subsidy_id="subsidy_1")
    world = queue_npc_order(world, SCENARIO, cut)

    with pytest.raises(CommandError) as error:
        queue_npc_order(world, SCENARIO, cut)

    assert error.value.code == "duplicate_slot"


def test_a_cut_that_goes_stale_before_resolving_is_refunded() -> None:
    world = _subsidized_world()
    world = queue_npc_order(
        world, SCENARIO, CutSubsidyOrder(faction_id=PAYER, subsidy_id="subsidy_1")
    )
    budget = world.factions[PAYER].orders_remaining
    world.pressure.subsidies = []

    result = run_phase(DiplomacyPhase(), world)

    command = result.world.accepted_commands[-1]
    assert command.failure_reason == "unknown_subsidy"
    assert result.world.factions[PAYER].orders_remaining == budget + 1


def test_a_subsidy_cannot_be_cut_before_it_exists() -> None:
    world, _ = _war_world()

    with pytest.raises(CommandError) as error:
        queue_npc_order(
            world, SCENARIO, CutSubsidyOrder(faction_id=PAYER, subsidy_id="subsidy_1")
        )

    assert error.value.code == "unknown_subsidy"


def test_subsidy_ends_when_the_war_ends_or_a_party_is_destroyed() -> None:
    world = _subsidized_world()
    payer_before = world.factions[PAYER].treasury
    world.factions[RECEIVER].is_destroyed = True

    pay_subsidies(world)

    assert world.pressure.subsidies == []
    assert world.factions[PAYER].treasury == payer_before

    ended = _subsidized_world()
    ended.wars = []
    result = run_phase(TimePhase(), ended)
    assert result.world.pressure.subsidies == []
    assert result.world.factions[PAYER].treasury >= 0
