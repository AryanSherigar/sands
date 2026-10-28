from app.config import Settings
from app.engine.stances.cadence import leaders_due_for_stance
from app.engine.stances.fallback import fallback_stance_id
from app.engine.stances.menu import resolve_stance_menu
from app.models.stance import StanceChoice, StanceRequest, StanceSource
from app.models.world_state import WorldState
from app.repositories import stance_request_repo
from app.services.stance_briefing import build_stance_briefing, stance_input_hash
from app.services.stance_service import (
    REASON_PROVIDER_DISABLED,
    is_stance_provider_ready,
)
from psycopg import AsyncConnection
from strategy_contracts.ids import LeaderId
from strategy_contracts.scenario import StrategyScenario

REASON_FALLBACK_DEFAULT = "fallback_default"
REASON_SINGLE_OPTION = "single_option"


async def schedule_stance_requests(
    connection: AsyncConnection,
    world: WorldState,
    scenario: StrategyScenario,
    settings: Settings,
    event_leaders: list[LeaderId] | None = None,
) -> None:
    """Queue next turn's stance requests; the world is left untouched so replay hashes match."""
    due_turn = world.clock.turn + 1
    leader_ids = set(leaders_due_for_stance(world, due_turn))
    leader_ids |= {item for item in event_leaders or [] if item in world.leaders}
    for leader_id in sorted(leader_ids):
        request = _build_request(world, scenario, settings, leader_id, due_turn)
        if request is None:
            continue
        reason_code = request.fallback.reason_code
        await stance_request_repo.insert_request(
            connection, request, is_fallback_only=reason_code != REASON_FALLBACK_DEFAULT
        )


def _build_request(
    world: WorldState,
    scenario: StrategyScenario,
    settings: Settings,
    leader_id: LeaderId,
    due_turn: int,
) -> StanceRequest | None:
    leader = world.leaders[leader_id]
    menu = resolve_stance_menu(scenario, leader.faction_id)
    if not menu:
        return None
    briefing = build_stance_briefing(world, scenario, leader_id)
    input_hash = stance_input_hash(briefing)
    fallback = StanceChoice(
        leader_id=leader_id,
        faction_id=leader.faction_id,
        due_turn=due_turn,
        option_id=fallback_stance_id(leader, menu, scenario),
        source=StanceSource.FALLBACK,
        reason_code=_fallback_reason(len(menu), settings),
        input_hash=input_hash,
    )
    return StanceRequest(
        playthrough_id=world.playthrough_id,
        request_id=f"stance:{leader_id}:{due_turn}",
        leader_id=leader_id,
        faction_id=leader.faction_id,
        due_turn=due_turn,
        input_hash=input_hash,
        briefing=briefing,
        fallback=fallback,
    )


def _fallback_reason(menu_size: int, settings: Settings) -> str:
    if menu_size == 1:
        return REASON_SINGLE_OPTION
    if not is_stance_provider_ready(settings):
        return REASON_PROVIDER_DISABLED
    return REASON_FALLBACK_DEFAULT
