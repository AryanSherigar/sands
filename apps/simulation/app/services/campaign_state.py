import hashlib
import json

from app.engine.battles.views import project_battle
from app.models.battle_progress import CampaignState, CampaignStatus, MutationResponse
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario


def request_hash(route_kind: str, payload: dict[str, object]) -> str:
    encoded = json.dumps([route_kind, payload], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def player_faction(world: WorldState) -> str:
    return next(
        identity for identity, faction in world.factions.items() if faction.is_player
    )


def campaign_status(world: WorldState, is_complete: bool = False) -> CampaignStatus:
    if is_complete:
        return "turn_completed"
    if world.progress.waiting_reason == "awaiting_commands":
        return "awaiting_commands"
    if world.progress.waiting_reason == "awaiting_battle_decision":
        return "awaiting_battle_decision"
    if world.progress.pending_scene_id is not None:
        return "awaiting_scene"
    return "planning"


def project_state(
    world: WorldState,
    scenario: StrategyScenario,
    version: int,
    digest: str,
    is_complete: bool = False,
) -> CampaignState:
    faction_id = player_faction(world)
    return CampaignState(
        playthrough_id=world.playthrough_id,
        world_version=version,
        world_hash=digest,
        turn=world.clock.turn,
        wave=world.progress.completed_waves,
        orders_remaining=world.factions[faction_id].orders_remaining,
        status=campaign_status(world, is_complete),
        scene_id=world.progress.pending_scene_id,
        battles=[
            project_battle(world, battle.id, faction_id, scenario)
            for battle in sorted(world.battles, key=lambda item: item.id)
            if faction_id in battle.contingents
        ],
    )


def mutation_response(
    state: CampaignState, operation_id: str, command_id: str | None = None
) -> MutationResponse:
    return MutationResponse(
        **state.model_dump(), operation_id=operation_id, accepted_command_id=command_id
    )
