from app.engine.economy.budget import next_turn_orders

from tests.engine.economy.builders import PLAYER, make_faction


def test_a_faction_without_debt_gets_the_full_budget() -> None:
    assert next_turn_orders(6, make_faction(PLAYER)) == 6


def test_a_shortfall_choice_takes_an_order_from_next_turn() -> None:
    assert next_turn_orders(6, make_faction(PLAYER, orders_debt=1)) == 5


def test_the_budget_never_goes_negative() -> None:
    assert next_turn_orders(2, make_faction(PLAYER, orders_debt=5)) == 0
