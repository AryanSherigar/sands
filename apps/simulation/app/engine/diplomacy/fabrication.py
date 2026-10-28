from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.grounds import grant_ground
from app.engine.diplomacy.reputation import shift_standing
from app.engine.rng import DeterministicRng
from app.engine.trait_axes import axis_totals
from app.models.orders import FabricateClaimOrder
from app.models.world_diplomacy import GroundState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import DiplomacyTuning, GroundKind
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis

PERCENT_LOW = 1
PERCENT_HIGH = 100


def start_forgery(
    world: WorldState, scenario: StrategyScenario, order: FabricateClaimOrder
) -> EventLogEntry:
    tuning = scenario.tuning.diplomacy
    ground = grant_ground(
        world,
        scenario,
        kind=GroundKind.CLAIM,
        holder_faction_id=order.faction_id,
        target_faction_id=order.target_faction_id,
        region_id=order.region_id,
        strength=tuning.fabricated_claim_strength,
    )
    ground.is_forged = True
    ground.suspect_level = 0
    ground.matures_turn = world.clock.turn + tuning.fabrication_turns
    ground.since_turn = ground.matures_turn
    return diplomacy_event("forgery_started", [ground.id, order.faction_id])


def exposure_chance_percent(
    suspect_level: int, cunning_total: int, tuning: DiplomacyTuning
) -> int:
    chance = suspect_level * cunning_total // tuning.exposure_chance_divisor
    return min(tuning.exposure_chance_cap_percent, chance)


def _exposing_rivals(
    world: WorldState, scenario: StrategyScenario, ground: GroundState
) -> list[tuple[str, int]]:
    rivals: list[tuple[str, int]] = []
    for faction_id in sorted(world.factions):
        faction = world.factions[faction_id]
        leader = world.leaders.get(faction.leader_id or "")
        if faction_id == ground.holder_faction_id or faction.is_destroyed:
            continue
        if leader is None or not leader.is_alive:
            continue
        cunning = axis_totals(leader, scenario)[TraitAxis.CUNNING]
        if cunning > 0:
            rivals.append((faction_id, cunning))
    return rivals


def _expose(
    world: WorldState,
    scenario: StrategyScenario,
    ground: GroundState,
    rival_id: str,
) -> EventLogEntry:
    holder_id = ground.holder_faction_id
    world.grounds = [item for item in world.grounds if item.id != ground.id]
    shift_standing(
        world.factions[holder_id],
        -scenario.tuning.diplomacy.exposure_reputation_cost,
        0,
    )
    grant_ground(
        world,
        scenario,
        kind=GroundKind.BROKEN_PROMISE,
        holder_faction_id=rival_id,
        target_faction_id=holder_id,
    )
    return diplomacy_event("forgery_exposed", [ground.id, holder_id, rival_id])


def _check_exposure(
    world: WorldState,
    scenario: StrategyScenario,
    ground: GroundState,
    rng: DeterministicRng,
) -> EventLogEntry | None:
    tuning = scenario.tuning.diplomacy
    for rival_id, cunning in _exposing_rivals(world, scenario, ground):
        chance = exposure_chance_percent(ground.suspect_level, cunning, tuning)
        roll = rng.fork("expose", ground.id, rival_id).roll_range(
            PERCENT_LOW, PERCENT_HIGH
        )
        if roll <= chance:
            return _expose(world, scenario, ground, rival_id)
    return None


def tick_forgeries(
    world: WorldState, scenario: StrategyScenario, rng: DeterministicRng
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    forged = sorted(
        (ground for ground in world.grounds if ground.is_forged),
        key=lambda ground: ground.id,
    )
    for ground in forged:
        ground.suspect_level += scenario.tuning.diplomacy.suspect_per_turn
        exposed = _check_exposure(world, scenario, ground, rng)
        if exposed is not None:
            events.append(exposed)
    return events
