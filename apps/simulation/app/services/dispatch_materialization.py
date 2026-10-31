from app.models.world_diplomacy import EnvoyState
from app.models.world_pressure import RumorState
from app.models.world_state import WorldState
from app.repositories import dispatch_delivery_repo
from psycopg import AsyncConnection
from strategy_contracts.agents import AgentView, DispatchBriefing


def _player_faction_id(world: WorldState) -> str:
    return next(key for key, faction in world.factions.items() if faction.is_player)


def _briefing(
    world: WorldState, rumor: RumorState, envoy: EnvoyState
) -> DispatchBriefing:
    assert envoy.agent is not None
    return DispatchBriefing(
        rumor_id=rumor.id,
        playthrough_id=world.playthrough_id,
        turn=rumor.turn,
        agent=AgentView(name=envoy.agent.name, traits=list(envoy.agent.traits)),
        about_faction_id=rumor.about_faction_id,
        topic=rumor.topic,
        reported_band=rumor.band,
    )


def build_dispatch_briefings(
    world: WorldState, previous: WorldState
) -> list[DispatchBriefing]:
    known = {rumor.id for rumor in previous.pressure.rumors}
    player_id = _player_faction_id(world)
    envoys = {envoy.id: envoy for envoy in world.envoys}
    briefings: list[DispatchBriefing] = []
    for rumor in sorted(world.pressure.rumors, key=lambda item: item.id):
        envoy = envoys.get(rumor.envoy_id)
        if rumor.id in known or rumor.observer_id != player_id:
            continue
        if envoy is not None and envoy.agent is not None:
            briefings.append(_briefing(world, rumor, envoy))
    return briefings


async def persist_dispatch_requests(
    connection: AsyncConnection, world: WorldState, previous: WorldState
) -> None:
    for briefing in build_dispatch_briefings(world, previous):
        await dispatch_delivery_repo.insert(connection, briefing)
