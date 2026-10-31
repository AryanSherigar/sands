from app.engine.pressure.subsidies import pay_subsidies
from app.models.world_pressure import SubsidyState
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

PAYER = CAUTIOUS_RIVAL
RECEIVER = WRATHFUL_RIVAL
PAYMENT_CALLS = 20


@settings(max_examples=25, deadline=None)
@given(
    amount=st.integers(min_value=1, max_value=60),
    turns=st.integers(min_value=1, max_value=12),
    treasury=st.integers(min_value=0, max_value=400),
    destroyed_turn=st.integers(min_value=0, max_value=PAYMENT_CALLS),
)
def test_payments_keep_treasuries_non_negative_and_conserve_gold(
    amount: int, turns: int, treasury: int, destroyed_turn: int
) -> None:
    world = make_world()
    war = add_war(world, attacker_id=RECEIVER, defender_id="house_ashford")
    world.factions[PAYER].treasury = treasury
    start = world.clock.turn
    world.pressure.subsidies.append(
        SubsidyState(
            id="subsidy_1",
            payer_id=PAYER,
            receiver_id=RECEIVER,
            war_id=war.id,
            expires_turn=start + turns - 1,
            amount_per_turn=amount,
        )
    )
    receiver_start = world.factions[RECEIVER].treasury

    for step in range(PAYMENT_CALLS):
        world.clock.turn = start + step
        if step == destroyed_turn:
            world.factions[RECEIVER].is_destroyed = True
        pay_subsidies(world)

    payer_loss = treasury - world.factions[PAYER].treasury
    assert world.factions[PAYER].treasury >= 0
    assert world.factions[RECEIVER].treasury >= 0
    assert payer_loss == world.factions[RECEIVER].treasury - receiver_start
