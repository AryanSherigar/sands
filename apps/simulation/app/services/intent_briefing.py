from app.config import Settings
from app.engine.battles.policy import select_intent
from app.engine.battles.views import intent_briefing
from app.engine.outrage.effects import has_press_bias
from app.models.battle_progress import IntentRequest
from app.models.world_battle import BattleStatus
from app.models.world_state import WorldState
from app.repositories import intent_request_repo
from psycopg import AsyncConnection
from strategy_contracts.scenario import StrategyScenario


async def schedule_intent_requests(
    connection: AsyncConnection,
    world: WorldState,
    scenario: StrategyScenario,
    settings: Settings,
) -> None:
    if not _provider_is_ready(settings):
        return
    for battle in sorted(world.battles, key=lambda item: item.id):
        if battle.status != BattleStatus.AWAITING_COMMANDS:
            continue
        await _schedule_battle(connection, world, scenario, battle.id)


async def _schedule_battle(
    connection: AsyncConnection,
    world: WorldState,
    scenario: StrategyScenario,
    battle_id: str,
) -> None:
    battle = next(item for item in world.battles if item.id == battle_id)
    for faction_id in sorted(battle.contingents):
        if world.factions[faction_id].is_player:
            continue
        briefing = intent_briefing(world, battle_id, faction_id, scenario)
        fallback = select_intent(
            briefing,
            scenario.tuning.battle,
            should_press=has_press_bias(world, scenario, faction_id),
        )
        request = IntentRequest(
            playthrough_id=world.playthrough_id,
            request_id=f"intent:{fallback.id}",
            battle_id=battle_id,
            faction_id=faction_id,
            campaign_turn=world.clock.turn,
            intended_wave=fallback.intended_wave,
            input_hash=fallback.input_hash,
            observation_fingerprint=fallback.observation_fingerprint,
            policy_version=fallback.policy_version,
            redacted_input=briefing,
            fallback=fallback,
        )
        await intent_request_repo.insert_request(connection, request)


def _provider_is_ready(settings: Settings) -> bool:
    return bool(
        settings.intent_provider_enabled
        and settings.intent_provider_url
        and settings.intent_provider_api_key
        and settings.intent_provider_model
    )
