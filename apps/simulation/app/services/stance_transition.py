from app.config import Settings
from app.engine.stances.cadence import major_event_leaders
from app.models.stance import StanceChoice
from app.models.world_state import WorldState
from app.repositories import stance_request_repo
from app.services.stance_scheduling import schedule_stance_requests
from psycopg import AsyncConnection
from strategy_contracts.ids import LeaderId
from strategy_contracts.scenario import StrategyScenario


async def freeze_next_stances(
    connection: AsyncConnection, world: WorldState
) -> dict[LeaderId, StanceChoice]:
    """Read (and row-lock) the answers due when the current turn completes."""
    return await stance_request_repo.freeze_stances(
        connection, world.playthrough_id, world.clock.turn + 1
    )


async def settle_stances(
    connection: AsyncConnection,
    before: WorldState,
    after: WorldState,
    scenario: StrategyScenario,
    settings: Settings,
    frozen: dict[LeaderId, StanceChoice],
) -> list[StanceChoice]:
    """Seal consumed requests, queue the next ones, and return the choices replay must reapply."""
    did_complete_turn = after.clock.turn > before.clock.turn
    if did_complete_turn:
        await stance_request_repo.activate_stances(
            connection, before.playthrough_id, before.clock.turn + 1
        )
    await schedule_stance_requests(
        connection,
        after,
        scenario,
        settings,
        event_leaders=major_event_leaders(before, after),
    )
    return (
        [frozen[leader_id] for leader_id in sorted(frozen)] if did_complete_turn else []
    )
