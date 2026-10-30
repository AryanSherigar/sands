from collections.abc import Iterable, Mapping, Sequence

from app.engine.movement.phase import MovementPhase
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.rng import derive_rng
from app.models.orders import HaltArmyOrder, MoveArmyOrder, QueuedOrder
from app.models.world_army import ArmyState, MarchState
from app.models.world_clock import RngState, TurnClock
from app.models.world_diplomacy import RelationState
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus, Terrain, TroopType
from strategy_contracts.map import MapDocument, MapRegion, Point, Road
from strategy_contracts.scenario import MovementTuning, StrategyScenario, Tuning

from tests.models.builders import PLAYTHROUGH_ID, make_faction, make_region

SEED = 7
SUMMER_START_MONTH = 6
WINTER_START_MONTH = 12
SPRING_START_MONTH = 3
DEFAULT_TROOPS = 100
DEFAULT_MORALE = 70
FACTION_A = "house_a"
FACTION_B = "house_b"
FACTION_C = "house_c"


def make_map(
    terrains: Mapping[str, Terrain],
    links: Iterable[tuple[str, str]],
    roads: Iterable[tuple[str, str]] = (),
) -> MapDocument:
    neighbors: dict[str, set[str]] = {region_id: set() for region_id in terrains}
    for left, right in links:
        neighbors[left].add(right)
        neighbors[right].add(left)
    regions = [
        MapRegion(
            id=region_id,
            name=region_id,
            terrain=terrain,
            outline="M0 0",
            label_point=Point(x=0, y=0),
            neighbor_ids=sorted(neighbors[region_id]),
        )
        for region_id, terrain in terrains.items()
    ]
    return MapDocument(
        regions=regions,
        roads=[Road(region_a=left, region_b=right) for left, right in roads],
    )


def make_scenario(
    map_document: MapDocument, **movement_overrides: object
) -> StrategyScenario:
    movement = MovementTuning(**movement_overrides)
    return StrategyScenario(map=map_document, tuning=Tuning(movement=movement))


def make_army(
    army_id: str,
    owner_id: str,
    location_id: str,
    troops: Mapping[TroopType, int] | None = None,
    morale: int = DEFAULT_MORALE,
    march: MarchState | None = None,
) -> ArmyState:
    return ArmyState(
        id=army_id,
        owner_id=owner_id,
        troops=dict(troops or {TroopType.INFANTRY: DEFAULT_TROOPS}),
        morale=morale,
        location_id=location_id,
        march=march,
    )


def make_world_for(
    region_owners: Mapping[str, str | None],
    armies: Sequence[ArmyState] = (),
    statuses: Mapping[tuple[str, str], RelationStatus] | None = None,
    start_month: int = SUMMER_START_MONTH,
    turn: int = 0,
) -> WorldState:
    faction_ids = sorted({FACTION_A, FACTION_B, FACTION_C})
    relations = [
        RelationState(faction_a=left, faction_b=right, status=status, since_turn=0)
        for (left, right), status in sorted((statuses or {}).items())
    ]
    return WorldState(
        playthrough_id=PLAYTHROUGH_ID,
        clock=TurnClock(turn=turn, start_year=1000, start_month=start_month),
        rng=RngState(seed=SEED),
        regions={
            region_id: make_region(region_id, owner_id)
            for region_id, owner_id in region_owners.items()
        },
        factions={
            faction_id: make_faction(faction_id, is_player=faction_id == FACTION_A)
            for faction_id in faction_ids
        },
        armies={army.id: army for army in armies},
        relations=relations,
        ruler=PlayerRuler(
            name="Valdren",
            trait_ids=["honorable", "cautious"],
            ambition_ids=["ambition_peace"],
        ),
    )


def move_order(
    order_id: str, army_id: str, destination: str, faction_id: str = FACTION_A
) -> QueuedOrder:
    order = MoveArmyOrder(
        faction_id=faction_id, army_id=army_id, to_region_id=destination
    )
    return QueuedOrder(id=order_id, order=order, cost=1, queued_turn=0)


def halt_order(order_id: str, army_id: str, faction_id: str = FACTION_A) -> QueuedOrder:
    order = HaltArmyOrder(faction_id=faction_id, army_id=army_id)
    return QueuedOrder(id=order_id, order=order, cost=0, queued_turn=0)


def run_movement(
    world: WorldState,
    scenario: StrategyScenario,
    orders: Sequence[QueuedOrder] = (),
) -> PhaseResult:
    rng = derive_rng(world.rng.seed, world.clock.turn, PhaseName.MOVEMENT.value)
    context = PhaseContext(
        scenario=scenario,
        orders=tuple(sorted(orders, key=lambda queued: queued.id)),
        rng=rng,
        resolved_outcomes={},
        recorded_answers={},
    )
    return MovementPhase().run(world.model_copy(deep=True), context)


def play_turns(
    world: WorldState,
    scenario: StrategyScenario,
    turns: int,
    first_turn_orders: Sequence[QueuedOrder] = (),
) -> tuple[WorldState, list[EventLogEntry]]:
    events: list[EventLogEntry] = []
    for index in range(turns):
        orders = first_turn_orders if index == 0 else ()
        result = run_movement(world, scenario, orders)
        events += result.events
        world = result.world
        world.clock.turn += 1
    return world, events


def kinds(events: Iterable[EventLogEntry]) -> list[str]:
    return [event.kind for event in events]
