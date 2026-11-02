import pytest
from app.engine.commands.check import check_command
from app.engine.commands.validation import validate_empire_command
from app.exceptions.command_exceptions import CommandError
from app.models.api_orders import OrderFlag
from app.models.orders import (
    BuildImprovementOrder,
    ProposeAgreementOrder,
)
from strategy_contracts.enums import ImprovementKind

from tests.engine.diplomacy.builders import CAUTIOUS_RIVAL, PLAYER, SCENARIO, make_world

UNIMPLEMENTED_ORDERS = [
    BuildImprovementOrder(
        faction_id=PLAYER,
        region_id="ashford",
        improvement_kind=ImprovementKind.BARRACKS,
    ),
    ProposeAgreementOrder(
        faction_id=PLAYER,
        target_faction_id=CAUTIOUS_RIVAL,
        agreement="alliance",
    ),
]


@pytest.mark.parametrize("order", UNIMPLEMENTED_ORDERS, ids=lambda o: o.kind)
def test_unimplemented_orders_raise_command_error_on_validation(order) -> None:
    world = make_world()
    with pytest.raises(CommandError) as raised:
        validate_empire_command(world, order, SCENARIO)

    assert raised.value.code == "unimplemented_order"
    assert raised.value.status_code == 422


@pytest.mark.parametrize("order", UNIMPLEMENTED_ORDERS, ids=lambda o: o.kind)
def test_unimplemented_orders_report_impossible_in_check_command(order) -> None:
    world = make_world()
    result = check_command(
        world,
        SCENARIO,
        order,
        faction_id=PLAYER,
        expected_turn=world.clock.turn,
        expected_wave=0,
    )

    assert result.flag == OrderFlag.IMPOSSIBLE
    assert result.reason == "unimplemented_order"
