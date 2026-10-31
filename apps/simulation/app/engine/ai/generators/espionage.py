from app.engine.ai.candidates import Candidate
from app.engine.ai.situation import war_enemies
from app.engine.pressure.agents import bribe_price
from app.engine.trait_axes import axis_totals
from app.models.orders import BribeEnvoyOrder
from app.models.world_diplomacy import EnvoyState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory
from strategy_contracts.traits import TraitAxis


def _hostile_senders(world: WorldState, faction_id: FactionId) -> set[FactionId]:
    senders = set(war_enemies(world, faction_id))
    aim = world.aims.get(faction_id)
    if aim is not None and aim.target_faction_id is not None:
        senders.add(aim.target_faction_id)
    return senders


def _is_target_envoy(envoy: EnvoyState, hostile: set[FactionId]) -> bool:
    agent = envoy.agent
    return (
        agent is not None
        and agent.bribed_by is None
        and envoy.from_faction_id in hostile
    )


def _can_afford(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    envoy: EnvoyState,
) -> bool:
    assert envoy.agent is not None
    price = bribe_price(envoy.agent, scenario.tuning.agents)
    remaining = world.factions[faction_id].treasury - price
    return remaining >= scenario.tuning.ai.low_treasury


def bribe_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.agents
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    if not tuning.is_enabled or leader is None:
        return []
    cunning = max(0, axis_totals(leader, scenario).get(TraitAxis.CUNNING, 0))
    hostile = _hostile_senders(world, faction_id)
    return [
        Candidate(
            BribeEnvoyOrder(faction_id=faction_id, envoy_id=envoy.id),
            ScoreCategory.ATTACK,
            tuning.bribe_score_bonus + cunning,
        )
        for envoy in sorted(world.envoys, key=lambda item: item.id)
        if envoy.at_faction_id == faction_id
        and _is_target_envoy(envoy, hostile)
        and _can_afford(world, scenario, faction_id, envoy)
    ]
