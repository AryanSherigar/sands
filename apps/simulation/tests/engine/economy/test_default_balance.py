from app.engine.economy.phase import EconomyPhase
from app.engine.economy.projection import project_balance
from app.engine.pipeline import run_turn
from app.engine.world_init import new_world
from app.models.orders import QueuedOrder, SetTaxRateOrder
from app.models.world_events import PHASE_ORDER, PhaseName
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from strategy_contracts.enums import TaxRate
from strategy_contracts.examples import load_three_crowns_expanded

from tests.engine.economy.builders import PLAYTHROUGH_ID, SCENE_ID
from tests.engine.toy_phases import ToyPhase

# NOTE: these pin the *feel* of the shipped EconomyTuning defaults on the example
# scenario, not exact numbers: calm by default, near break-even at double the
# army, a real spiral at triple, and high taxes that pay for a while then bite.
SCENARIO = load_three_crowns_expanded()
PLAYER = "house_ashford"
CALM_RANGE_PERCENT = (30, 75)
DOUBLE_ARMY_MIN_PERCENT = 80
HIGH_TAX_TURNS = 30
HIGH_TAX_EARLY_TURN = 6
PERCENT = 100


def _start() -> WorldState:
    ruler = PlayerRuler(
        name="Valdren",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
    )
    return new_world(SCENARIO, PLAYTHROUGH_ID, 1, PLAYER, ruler)


def _upkeep_share(world: WorldState, faction_id: str) -> int:
    projection = project_balance(world, SCENARIO, faction_id, [])
    return projection.upkeep * PERCENT // projection.income


def _scale_armies(world: WorldState, faction_id: str, factor: int) -> None:
    for army in world.armies.values():
        if army.owner_id == faction_id:
            army.troops = {kind: count * factor for kind, count in army.troops.items()}


def _treasuries(tax_rate: TaxRate, turns: int) -> list[int]:
    phases = {name: ToyPhase(name, lambda *_: None) for name in PHASE_ORDER}
    phases[PhaseName.ECONOMY] = EconomyPhase()
    order = SetTaxRateOrder(faction_id=PLAYER, tax_rate=tax_rate)
    orders = [QueuedOrder(id="order_1", order=order, cost=1, queued_turn=0)]
    world, treasuries = _start(), []
    for turn in range(turns):
        result = run_turn(world, SCENARIO, orders if turn == 0 else [], phases, {}, {})
        assert result.pause is None, SCENE_ID
        world = result.world
        treasuries.append(world.factions[PLAYER].treasury)
    return treasuries


def test_starting_armies_are_affordable_but_not_free() -> None:
    world = _start()
    low, high = CALM_RANGE_PERCENT
    for faction_id in world.factions:
        assert low <= _upkeep_share(world, faction_id) <= high, faction_id


def test_doubling_the_army_leaves_almost_no_slack() -> None:
    world = _start()
    _scale_armies(world, PLAYER, 2)
    share = _upkeep_share(world, PLAYER)
    assert DOUBLE_ARMY_MIN_PERCENT <= share <= PERCENT


def test_tripling_the_army_runs_a_standing_deficit() -> None:
    world = _start()
    _scale_armies(world, PLAYER, 3)
    projection = project_balance(world, SCENARIO, PLAYER, [])
    assert projection.upkeep > projection.income


def test_high_taxes_pay_early_then_fall_behind_normal_taxes() -> None:
    high = _treasuries(TaxRate.HIGH, HIGH_TAX_TURNS)
    normal = _treasuries(TaxRate.NORMAL, HIGH_TAX_TURNS)
    assert high[HIGH_TAX_EARLY_TURN] > normal[HIGH_TAX_EARLY_TURN]
    assert high[-1] < normal[-1]


RECRUIT_MIN_TURNS_OF_INCOME = 4


def test_raising_a_second_starting_army_costs_several_turns_of_income() -> None:
    world = _start()
    economy = SCENARIO.tuning.economy
    troops = [
        (kind, count)
        for army in world.armies.values()
        if army.owner_id == PLAYER
        for kind, count in army.troops.items()
    ]
    cost = sum(
        count * economy.recruit_cost_per_unit[kind] // economy.upkeep_troop_unit
        for kind, count in troops
    )
    income = project_balance(world, SCENARIO, PLAYER, []).income

    assert cost >= RECRUIT_MIN_TURNS_OF_INCOME * income
