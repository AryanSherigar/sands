from app.engine.rng import DeterministicRng
from app.engine.succession.health import death_per_mille
from app.models.world_character import LeaderState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import PER_MILLE

CAUSE_OLD_AGE = "old_age"
CAUSE_ILLNESS = "illness"
ROLL_STREAM = "ruler_death"


def mortal_ruler(world: WorldState, faction_id: FactionId) -> LeaderState | None:
    faction = world.factions[faction_id]
    if faction.is_player or faction.is_destroyed or faction.leader_id is None:
        return None
    leader = world.leaders.get(faction.leader_id)
    if leader is None or not leader.is_alive:
        return None
    return leader


def _cause_of(leader: LeaderState, scenario: StrategyScenario) -> str:
    if leader.age >= scenario.tuning.succession.failing_age:
        return CAUSE_OLD_AGE
    return CAUSE_ILLNESS


def _dies(
    world: WorldState,
    scenario: StrategyScenario,
    leader: LeaderState,
    rng: DeterministicRng,
) -> bool:
    stream = rng.fork(ROLL_STREAM, leader.id, world.clock.turn)
    return stream.roll(PER_MILLE) < death_per_mille(leader, scenario)


def roll_ruler_deaths(
    world: WorldState, scenario: StrategyScenario, rng: DeterministicRng
) -> list[tuple[FactionId, str]]:
    if not world.succession_ruleset:
        return []
    deaths: list[tuple[FactionId, str]] = []
    for faction_id in sorted(world.factions):
        leader = mortal_ruler(world, faction_id)
        if leader is not None and _dies(world, scenario, leader, rng):
            deaths.append((faction_id, _cause_of(leader, scenario)))
    return deaths
