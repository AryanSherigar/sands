"""Campaign initialization service and seed parser."""

from uuid import UUID

from app.engine.world_init import new_world
from app.exceptions.command_exceptions import CommandError
from app.models.campaign import InitializeCampaign
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from app.services.campaign_initialization import initialize_campaign, validate_initialization
from strategy_contracts.scenario import StrategyScenario


def parse_seed_and_init_world(
    scenario: StrategyScenario,
    playthrough_id: UUID,
    seed: int,
    player_faction_id: str,
    ruler: PlayerRuler,
) -> WorldState:
    """Parse scenario definition and RNG seed into live simulation world state."""
    return new_world(
        scenario=scenario,
        playthrough_id=playthrough_id,
        seed=seed,
        player_faction_id=player_faction_id,
        ruler=ruler,
    )


__all__ = [
    "new_world",
    "parse_seed_and_init_world",
    "initialize_campaign",
    "validate_initialization",
]
