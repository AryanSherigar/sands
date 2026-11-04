from collections.abc import Iterable, Mapping, Sequence
from uuid import UUID

from app.engine.economy.phase import EconomyPhase
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.rng import derive_rng
from app.models.orders import Order, QueuedOrder
from app.models.world_army import ArmyState, MarchState
from app.models.world_clock import RngState, TurnClock
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_faction import FactionState
from app.models.world_player import PlayerRuler
from app.models.world_region import RegionState
from app.models.world_state import WorldState
from strategy_contracts.enums import PayLevel, TaxRate, TroopType
from strategy_contracts.scenario import (
    EconomyTuning,
    StrategyScenario,
    SystemToggles,
    Tuning,
)
from strategy_contracts.scene import SceneOutcome

PLAYTHROUGH_ID = UUID("66666666-6666-6666-6666-666666666666")
SCENE_ID = UUID("77777777-7777-7777-7777-777777777777")
SEED = 11
PLAYER = "house_a"
RIVAL = "house_b"
HOME = "home"
ELSEWHERE = "elsewhere"


# NOTE: unit tests pin their own numbers so tuning the shipped defaults
# (test_default_balance.py covers those) never churns them.
TEST_TUNING_FIELDS: dict[str, object] = {
    "tax_rate_percent": {TaxRate.LOW: 60, TaxRate.NORMAL: 100, TaxRate.HIGH: 150},
    "recruit_cost_per_unit": {
        TroopType.INFANTRY: 25,
        TroopType.CAVALRY: 60,
        TroopType.ARCHERS_SIEGE: 75,
    },
    "manpower_refill_per_thousand": 20,
    "manpower_cap_percent": 20,
}
TEST_TUNING = EconomyTuning(**TEST_TUNING_FIELDS)


def make_scenario(
    is_loans_enabled: bool = True, **economy_overrides: object
) -> StrategyScenario:
    economy = EconomyTuning(**(TEST_TUNING_FIELDS | economy_overrides))
    return StrategyScenario(
        toggles=SystemToggles(is_loans_enabled=is_loans_enabled),
        tuning=Tuning(economy=economy),
    )


def make_region(
    region_id: str,
    owner_id: str | None,
    population: int = 500,
    wealth: int = 100,
    manpower: int = 50,
    unrest: int = 0,
    **overrides: object,
) -> RegionState:
    return RegionState(
        id=region_id,
        owner_id=owner_id,
        population=population,
        wealth=wealth,
        manpower=manpower,
        unrest=unrest,
        garrison=0,
        faith_id=None,
        **overrides,
    )


def make_faction(
    faction_id: str,
    treasury: int = 100,
    is_player: bool = False,
    tax_rate: TaxRate = TaxRate.NORMAL,
    **overrides: object,
) -> FactionState:
    return FactionState(
        id=faction_id,
        leader_id=None,
        treasury=treasury,
        stability=60,
        war_exhaustion=0,
        reputation=0,
        tax_rate=tax_rate,
        orders_remaining=6,
        is_player=is_player,
        **overrides,
    )


def make_army(
    army_id: str,
    owner_id: str,
    location_id: str = HOME,
    troops: Mapping[TroopType, int] | None = None,
    morale: int = 50,
    pay_level: PayLevel = PayLevel.FULL,
    march: MarchState | None = None,
    **overrides: object,
) -> ArmyState:
    return ArmyState(
        id=army_id,
        owner_id=owner_id,
        troops=dict(troops or {TroopType.INFANTRY: 200}),
        morale=morale,
        location_id=location_id,
        pay_level=pay_level,
        march=march,
        **overrides,
    )


def make_world(
    regions: Iterable[RegionState] = (),
    factions: Iterable[FactionState] = (),
    armies: Iterable[ArmyState] = (),
) -> WorldState:
    return WorldState(
        playthrough_id=PLAYTHROUGH_ID,
        clock=TurnClock(turn=0, start_year=1000, start_month=3),
        rng=RngState(seed=SEED),
        regions={region.id: region for region in regions},
        factions={faction.id: faction for faction in factions},
        armies={army.id: army for army in armies},
        ruler=PlayerRuler(
            name="Valdren",
            trait_ids=["honorable", "cautious"],
            ambition_ids=["ambition_peace"],
        ),
    )


def queued(order: Order, order_id: str = "order_1") -> QueuedOrder:
    return QueuedOrder(id=order_id, order=order, cost=1, queued_turn=0)


def run_economy(
    world: WorldState,
    scenario: StrategyScenario | None = None,
    orders: Sequence[QueuedOrder] = (),
    outcomes: Mapping[UUID, SceneOutcome] | None = None,
) -> PhaseResult:
    scenario = scenario or make_scenario()
    context = PhaseContext(
        scenario=scenario,
        orders=tuple(orders),
        rng=derive_rng(world.rng.seed, world.clock.turn, PhaseName.ECONOMY.value),
        resolved_outcomes=outcomes or {},
        recorded_answers={},
    )
    return EconomyPhase().run(world.model_copy(deep=True), context)


def events_of(result: PhaseResult, kind: str) -> list[EventLogEntry]:
    return [event for event in result.events if event.kind == kind]


def kinds_of(result: PhaseResult) -> list[str]:
    return [event.kind for event in result.events]
