import pytest
from app.models.orders import (
    DeclareDefaultOrder,
    DisbandArmyOrder,
    RaiseArmyOrder,
    SetPayOrder,
    SetTaxRateOrder,
    TakeLoanOrder,
)
from app.models.world_character import CommanderState
from app.models.world_events import PendingBattle
from app.models.world_region import OccupationState
from strategy_contracts.enums import PayLevel, TaxRate, TroopType

from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    RIVAL,
    events_of,
    make_army,
    make_faction,
    make_region,
    make_scenario,
    make_world,
    queued,
    run_economy,
)


def _world(**faction_overrides: object):
    return make_world(
        regions=[make_region(HOME, PLAYER, wealth=100, manpower=80)],
        factions=[
            make_faction(PLAYER, treasury=500, **faction_overrides),
            make_faction(RIVAL),
        ],
        armies=[make_army("army_x", PLAYER)],
    )


def _rejection(result) -> str:
    [event] = events_of(result, "economy_order_rejected")
    return event.cause.summary_key


def test_set_tax_rate_changes_the_rate_and_is_logged() -> None:
    order = queued(SetTaxRateOrder(faction_id=PLAYER, tax_rate=TaxRate.HIGH))
    result = run_economy(_world(), orders=[order])
    [event] = events_of(result, "tax_rate_set")
    assert result.world.factions[PLAYER].tax_rate is TaxRate.HIGH
    assert (event.changes[0].before, event.changes[0].after) == ("normal", "high")


def test_the_new_tax_rate_applies_to_this_turns_income() -> None:
    order = queued(SetTaxRateOrder(faction_id=PLAYER, tax_rate=TaxRate.HIGH))
    high = run_economy(_world(), orders=[order])
    normal = run_economy(_world())
    assert high.world.factions[PLAYER].treasury > normal.world.factions[PLAYER].treasury


def test_set_pay_changes_the_armys_pay_level() -> None:
    order = queued(
        SetPayOrder(faction_id=PLAYER, army_id="army_x", pay_level=PayLevel.REDUCED)
    )
    result = run_economy(_world(), orders=[order])
    assert result.world.armies["army_x"].pay_level is PayLevel.REDUCED
    assert len(events_of(result, "pay_set")) == 1


def test_set_pay_on_someone_elses_army_is_rejected() -> None:
    world = make_world(
        factions=[make_faction(PLAYER), make_faction(RIVAL)],
        armies=[make_army("army_y", RIVAL)],
    )
    order = queued(
        SetPayOrder(faction_id=PLAYER, army_id="army_y", pay_level=PayLevel.REDUCED)
    )
    result = run_economy(world, orders=[order])
    assert _rejection(result) == "economy_order_rejected_not_your_army"
    assert result.world.armies["army_y"].pay_level is PayLevel.FULL


def test_orders_from_an_unknown_faction_are_rejected() -> None:
    order = queued(SetTaxRateOrder(faction_id="house_zz", tax_rate=TaxRate.LOW))
    assert _rejection(run_economy(_world(), orders=[order])).endswith("unknown_faction")


def test_a_loan_order_adds_cash_and_a_debt_that_costs_interest_later() -> None:
    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=300))
    result = run_economy(_world(), orders=[order])
    [loan] = result.world.factions[PLAYER].loans
    assert loan.principal == 300
    assert loan.interest_percent == 4
    [event] = events_of(result, "loan_taken")
    assert event.cause.inputs["granted"] == 300


def test_a_loan_is_capped_by_available_credit() -> None:
    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=999_999))
    result = run_economy(_world(), orders=[order])
    [loan] = result.world.factions[PLAYER].loans
    assert loan.principal == 1000
    [event] = events_of(result, "loan_taken")
    assert event.cause.inputs["requested"] == 999_999


@pytest.mark.parametrize(
    ("amount", "is_loans_enabled", "reason"),
    [(0, True, "invalid_amount"), (50, False, "loans_disabled")],
)
def test_bad_loan_orders_are_rejected(
    amount: int, is_loans_enabled: bool, reason: str
) -> None:
    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=amount))
    scenario = make_scenario(is_loans_enabled=is_loans_enabled)
    result = run_economy(_world(), scenario, orders=[order])
    assert _rejection(result).endswith(reason)
    assert result.world.factions[PLAYER].loans == []


def test_no_loan_without_credit() -> None:
    world = make_world(
        factions=[make_faction(PLAYER, treasury=0)],
    )
    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=50))
    assert _rejection(run_economy(world, orders=[order])).endswith("no_credit")


def test_declare_default_is_logged() -> None:
    order = queued(DeclareDefaultOrder(faction_id=PLAYER))
    assert (
        len(events_of(run_economy(_world(), orders=[order]), "default_declared")) == 1
    )


def test_raising_an_army_spends_manpower_and_gold() -> None:
    order = queued(
        RaiseArmyOrder(
            faction_id=PLAYER, region_id=HOME, troops={TroopType.INFANTRY: 40}
        )
    )
    scenario = make_scenario(morale_recovery={PayLevel.FULL: 0, PayLevel.REDUCED: 0})
    result = run_economy(_world(), scenario, orders=[order])
    [event] = events_of(result, "army_raised")
    raised = result.world.armies["army_1"]
    assert raised.troops == {TroopType.INFANTRY: 40}
    assert (raised.owner_id, raised.location_id, raised.morale) == (PLAYER, HOME, 60)
    assert event.cause.inputs["recruit_cost"] == 10
    assert result.world.regions[HOME].manpower == 80 - 40 + 10


def test_raised_army_ids_never_collide_with_existing_ones() -> None:
    world = _world()
    world.armies["army_1"] = make_army("army_1", PLAYER)
    order = queued(
        RaiseArmyOrder(
            faction_id=PLAYER, region_id=HOME, troops={TroopType.INFANTRY: 5}
        )
    )
    result = run_economy(world, orders=[order])
    assert "army_2" in result.world.armies


@pytest.mark.parametrize(
    ("troops", "reason"),
    [
        ({TroopType.INFANTRY: 0}, "empty_levy"),
        ({TroopType.INFANTRY: 81}, "insufficient_manpower"),
        ({TroopType.CAVALRY: 80}, "insufficient_funds"),
    ],
)
def test_bad_levies_are_rejected(troops: dict[TroopType, int], reason: str) -> None:
    world = _world()
    world.factions[PLAYER].treasury = 20
    order = queued(RaiseArmyOrder(faction_id=PLAYER, region_id=HOME, troops=troops))
    result = run_economy(world, orders=[order])
    assert len(result.world.armies) == 1
    assert _rejection(result).endswith(reason)


def test_a_levy_the_treasury_cannot_afford_is_rejected() -> None:
    world = _world()
    world.factions[PLAYER].treasury = 5
    order = queued(
        RaiseArmyOrder(
            faction_id=PLAYER, region_id=HOME, troops={TroopType.INFANTRY: 40}
        )
    )
    assert _rejection(run_economy(world, orders=[order])).endswith("insufficient_funds")


def test_cannot_raise_in_an_occupied_or_foreign_region() -> None:
    occupied = make_region(
        "lost",
        PLAYER,
        manpower=80,
        occupation=OccupationState(occupier_id=RIVAL, siege_progress=0),
    )
    world = make_world(
        regions=[occupied, make_region("theirs", RIVAL, manpower=80)],
        factions=[make_faction(PLAYER, treasury=500), make_faction(RIVAL)],
    )
    orders = [
        queued(
            RaiseArmyOrder(
                faction_id=PLAYER, region_id=region_id, troops={TroopType.INFANTRY: 5}
            ),
            order_id=f"order_{region_id}",
        )
        for region_id in ("lost", "theirs")
    ]
    result = run_economy(world, orders=orders)
    reasons = sorted(
        e.cause.summary_key for e in events_of(result, "economy_order_rejected")
    )
    assert reasons == [
        "economy_order_rejected_not_your_region",
        "economy_order_rejected_region_occupied",
    ]
    assert result.world.armies == {}


def test_disbanding_removes_the_army_and_returns_part_of_the_levy_home() -> None:
    world = _world()
    world.regions[HOME].manpower = 0
    order = queued(DisbandArmyOrder(faction_id=PLAYER, army_id="army_x"))
    result = run_economy(world, orders=[order])
    [event] = events_of(result, "army_disbanded")
    assert "army_x" not in result.world.armies
    assert event.cause.inputs["manpower_returned"] == 100
    assert result.world.regions[HOME].manpower == 100


def test_disbanding_far_from_home_loses_the_manpower() -> None:
    world = make_world(
        regions=[make_region(HOME, PLAYER, manpower=80), make_region("far", RIVAL)],
        factions=[make_faction(PLAYER), make_faction(RIVAL)],
        armies=[make_army("army_x", PLAYER, location_id="far")],
    )
    order = queued(DisbandArmyOrder(faction_id=PLAYER, army_id="army_x"))
    result = run_economy(world, orders=[order])
    [event] = events_of(result, "army_disbanded")
    assert event.cause.inputs["manpower_returned"] == 0
    assert result.world.regions[HOME].manpower == 90


def test_disbanding_frees_the_commander() -> None:
    world = _world()
    world.armies["army_x"].commander_id = "cmdr_one"
    world.commanders["cmdr_one"] = CommanderState(
        id="cmdr_one", faction_id=PLAYER, name="Harl", army_id="army_x"
    )
    order = queued(DisbandArmyOrder(faction_id=PLAYER, army_id="army_x"))
    result = run_economy(world, orders=[order])
    assert result.world.commanders["cmdr_one"].army_id is None


def test_an_army_in_an_open_battle_cannot_be_disbanded() -> None:
    world = _world()
    world.pending_battles.append(
        PendingBattle(
            id="battle_1",
            region_id=HOME,
            attacker_army_ids=["army_x"],
            defender_army_ids=[],
            is_big=False,
            status="awaiting_commands",
        )
    )
    order = queued(DisbandArmyOrder(faction_id=PLAYER, army_id="army_x"))
    result = run_economy(world, orders=[order])
    assert "army_x" in result.world.armies
    assert _rejection(result).endswith("in_battle")


def test_orders_apply_in_queue_id_order() -> None:
    first = queued(SetTaxRateOrder(faction_id=PLAYER, tax_rate=TaxRate.LOW), "order_1")
    second = queued(
        SetTaxRateOrder(faction_id=PLAYER, tax_rate=TaxRate.HIGH), "order_2"
    )
    result = run_economy(_world(), orders=[second, first])
    assert result.world.factions[PLAYER].tax_rate is TaxRate.HIGH
