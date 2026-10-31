from app.engine.ai.candidates import Candidate
from app.engine.ai.knowledge import build_knowledge
from app.engine.ai.situation import war_enemies
from app.engine.trait_axes import axis_totals
from app.models.orders import SendEnvoyOrder
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory
from strategy_contracts.traits import TraitAxis


def _is_candidate_host(
    world: WorldState, faction_id: FactionId, host_id: FactionId
) -> bool:
    host = world.factions[host_id]
    has_envoy = any(
        (envoy.from_faction_id, envoy.at_faction_id) == (faction_id, host_id)
        for envoy in world.envoys
    )
    return (
        host_id != faction_id
        and not host.is_player
        and not host.is_destroyed
        and host.leader_id is not None
        and not has_envoy
    )


def _bordering_hosts(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> set[FactionId]:
    knowledge = build_knowledge(world, scenario, faction_id)
    hosts: set[FactionId] = set()
    for region in world.regions.values():
        if region.owner_id != faction_id:
            continue
        for neighbor in knowledge.index.neighbors.get(region.id, frozenset()):
            owner_id = knowledge.owners.get(neighbor)
            if owner_id is not None and owner_id != faction_id:
                hosts.add(owner_id)
    return hosts


def _priority_hosts(world: WorldState, faction_id: FactionId) -> set[FactionId]:
    hosts = set(war_enemies(world, faction_id))
    aim = world.aims.get(faction_id)
    if aim is not None and aim.target_faction_id is not None:
        hosts.add(aim.target_faction_id)
    return hosts


def envoy_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    tuning = scenario.tuning.ai
    leader = world.leaders.get(world.factions[faction_id].leader_id or "")
    if leader is None:
        return []
    priority = _priority_hosts(world, faction_id)
    hosts = set(priority)
    if axis_totals(leader, scenario).get(TraitAxis.CUNNING, 0) > 0:
        hosts |= _bordering_hosts(world, scenario, faction_id)
    return [
        Candidate(
            SendEnvoyOrder(faction_id=faction_id, target_faction_id=host_id),
            ScoreCategory.EXPAND,
            tuning.envoy_bonus
            + (tuning.envoy_target_bonus if host_id in priority else 0),
        )
        for host_id in sorted(hosts)
        if _is_candidate_host(world, faction_id, host_id)
    ]
