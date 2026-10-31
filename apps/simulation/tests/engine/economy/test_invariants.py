import itertools

from app.engine.economy.reasons import SHORTFALL_CHOICES
from app.engine.phases import PhaseResult
from app.models.orders import (
    DeclareDefaultOrder,
    DisbandArmyOrder,
    Order,
    RaiseArmyOrder,
    SetPayOrder,
    SetTaxRateOrder,
    TakeLoanOrder,
)
from app.models.world_faction import LoanState
from app.models.world_state import WorldState
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from strategy_contracts.enums import PayLevel, TaxRate, TroopType
from strategy_contracts.scene import ChoiceOutcome

from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    SCENE_ID,
    make_army,
    make_faction,
    make_region,
    make_world,
    queued,
    run_economy,
)

PROPERTY_SETTINGS = settings(
    max_examples=60,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
REGION_IDS = ("reg_a", "reg_b", "reg_c")
ARMY_IDS = ("army_a", "army_b", "army_c")
OWNERS = (PLAYER, RIVAL, None)
FACTIONS = (PLAYER, RIVAL)
MAX_TREASURY = 400
MAX_TROOPS = 600
PERCENT = 100


@st.composite
def worlds(draw) -> WorldState:
    regions = [
        make_region(
            region_id,
            draw(st.sampled_from(OWNERS)),
            population=draw(st.integers(0, 2000)),
            wealth=draw(st.integers(0, 300)),
            manpower=draw(st.integers(0, 100)),
            unrest=draw(st.integers(0, PERCENT)),
        )
        for region_id in REGION_IDS
    ]
    factions = [
        make_faction(
            faction_id,
            treasury=draw(st.integers(0, MAX_TREASURY)),
            is_player=faction_id == PLAYER,
            tax_rate=draw(st.sampled_from(list(TaxRate))),
            credit_strikes=draw(st.integers(0, 4)),
            loans=draw(st.lists(loans(), max_size=2)),
        )
        for faction_id in FACTIONS
    ]
    armies = [
        make_army(
            army_id,
            draw(st.sampled_from(FACTIONS)),
            location_id=draw(st.sampled_from(REGION_IDS)),
            troops={
                troop_type: draw(st.integers(0, MAX_TROOPS)) for troop_type in TroopType
            },
            morale=draw(st.integers(0, PERCENT)),
            pay_level=draw(st.sampled_from(list(PayLevel))),
            unpaid_turns=draw(st.integers(0, 3)),
        )
        for army_id in draw(st.lists(st.sampled_from(ARMY_IDS), unique=True))
    ]
    return make_world(regions, factions, armies)


@st.composite
def loans(draw) -> LoanState:
    return LoanState(
        principal=draw(st.integers(1, 300)),
        interest_percent=draw(st.integers(0, 20)),
        turns_remaining=draw(st.integers(0, 12)),
    )


def _order_strategies() -> list[st.SearchStrategy[Order]]:
    return [
        st.builds(
            SetTaxRateOrder,
            faction_id=st.sampled_from(FACTIONS),
            tax_rate=st.sampled_from(list(TaxRate)),
        ),
        st.builds(
            SetPayOrder,
            faction_id=st.sampled_from(FACTIONS),
            army_id=st.sampled_from(ARMY_IDS),
            pay_level=st.sampled_from(list(PayLevel)),
        ),
        st.builds(
            TakeLoanOrder,
            faction_id=st.sampled_from(FACTIONS),
            amount=st.integers(-10, 500),
        ),
        st.builds(DeclareDefaultOrder, faction_id=st.sampled_from(FACTIONS)),
        st.builds(
            DisbandArmyOrder,
            faction_id=st.sampled_from(FACTIONS),
            army_id=st.sampled_from(ARMY_IDS),
        ),
        st.builds(
            RaiseArmyOrder,
            faction_id=st.sampled_from(FACTIONS),
            region_id=st.sampled_from(REGION_IDS),
            troops=st.dictionaries(
                st.sampled_from(list(TroopType)), st.integers(0, 120), max_size=3
            ),
        ),
    ]


@st.composite
def order_lists(draw):
    orders = draw(st.lists(st.one_of(_order_strategies()), max_size=6))
    return [queued(order, f"order_{index:02d}") for index, order in enumerate(orders)]


def _settle(world: WorldState, orders, choice: str) -> PhaseResult:
    result = run_economy(world, orders=orders)
    if result.pause is None:
        return result
    resumable = world.model_copy(deep=True)
    resumable.progress.pending_scene_id = SCENE_ID
    outcomes = {SCENE_ID: ChoiceOutcome(option_id=choice)}
    return run_economy(resumable, orders=orders, outcomes=outcomes)


def _treasury_chain(result: PhaseResult, faction_id: str) -> list[tuple[int, int]]:
    path = f"factions.{faction_id}.treasury"
    return [
        (change.before, change.after)
        for event in result.events
        for change in event.changes
        if change.path == path
    ]


@PROPERTY_SETTINGS
@given(worlds(), order_lists(), st.sampled_from(SHORTFALL_CHOICES))
def test_every_gold_change_is_logged_and_the_books_balance(
    world: WorldState, orders, choice: str
) -> None:
    result = _settle(world, orders, choice)
    for faction_id in FACTIONS:
        chain = _treasury_chain(result, faction_id)
        before = world.factions[faction_id].treasury
        after = result.world.factions[faction_id].treasury
        links = [(before, before), *chain, (after, after)]
        assert all(left[1] == right[0] for left, right in itertools.pairwise(links))


@PROPERTY_SETTINGS
@given(worlds(), order_lists(), st.sampled_from(SHORTFALL_CHOICES))
def test_the_economy_never_overdraws_a_treasury(
    world: WorldState, orders, choice: str
) -> None:
    result = _settle(world, orders, choice)
    assert all(faction.treasury >= 0 for faction in result.world.factions.values())


@PROPERTY_SETTINGS
@given(worlds(), order_lists(), st.sampled_from(SHORTFALL_CHOICES))
def test_numbers_stay_inside_their_bounds(
    world: WorldState, orders, choice: str
) -> None:
    result = _settle(world, orders, choice).world
    assert all(region.manpower >= 0 for region in result.regions.values())
    assert all(0 <= region.unrest <= PERCENT for region in result.regions.values())
    for army in result.armies.values():
        assert 0 <= army.morale <= PERCENT
        assert all(count >= 0 for count in army.troops.values())
        assert sum(army.troops.values()) > 0 or army.id in world.armies
    for faction in result.factions.values():
        assert -PERCENT <= faction.reputation <= PERCENT
        assert all(loan.principal > 0 for loan in faction.loans)


@PROPERTY_SETTINGS
@given(worlds(), order_lists(), st.sampled_from(SHORTFALL_CHOICES))
def test_manpower_is_conserved_apart_from_logged_levies_and_refills(
    world: WorldState, orders, choice: str
) -> None:
    result = _settle(world, orders, choice)
    logged = sum(
        change.after - change.before
        for event in result.events
        for change in event.changes
        if change.path.endswith(".manpower")
    )
    before = sum(region.manpower for region in world.regions.values())
    after = sum(region.manpower for region in result.world.regions.values())
    assert after - before == logged


@PROPERTY_SETTINGS
@given(worlds(), order_lists(), st.sampled_from(SHORTFALL_CHOICES))
def test_the_same_inputs_always_give_the_same_result(
    world: WorldState, orders, choice: str
) -> None:
    first = _settle(world, orders, choice)
    second = _settle(world, orders, choice)
    assert first.world.model_dump_json() == second.world.model_dump_json()
    assert first.events == second.events


@PROPERTY_SETTINGS
@given(worlds(), order_lists())
def test_a_pause_never_changes_the_input_world(world: WorldState, orders) -> None:
    before = world.model_dump_json()
    run_economy(world, orders=orders)
    assert world.model_dump_json() == before
