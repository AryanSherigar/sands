import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from app.models.world_events import SummaryRequest
from app.models.world_state import WorldState
from app.repositories import summary_delivery_repo
from psycopg import AsyncConnection
from strategy_contracts.summary import SummaryBriefing


def briefing_hash(briefing: SummaryBriefing) -> str:
    content = json.dumps(
        briefing.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(content.encode()).hexdigest()


def build_summary_briefing(
    world: WorldState, request: SummaryRequest
) -> SummaryBriefing:
    observer = next(key for key, faction in world.factions.items() if faction.is_player)
    return SummaryBriefing(
        summary_id=uuid5(NAMESPACE_URL, f"{world.playthrough_id}:{request.id}"),
        playthrough_id=world.playthrough_id,
        observer_faction_id=observer,
        chronicler_id=world.ruler.chronicler_id,
        requested_turn=request.requested_turn,
        trigger=request.trigger,
        facts=request.facts,
    )


async def persist_summary_requests(
    connection: AsyncConnection, world: WorldState, previous: WorldState
) -> None:
    existing = {item.id for item in previous.summary_requests}
    for request in world.summary_requests:
        if request.id in existing or not request.facts:
            continue
        package = build_summary_briefing(world, request)
        await summary_delivery_repo.insert(
            connection, package, request.id, briefing_hash(package)
        )
