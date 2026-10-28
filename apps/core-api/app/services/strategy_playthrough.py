"""Pure helpers for starting a strategy playthrough from a frozen snapshot."""

import uuid

from app.exceptions.playthrough_exceptions import (
    StrategyFactionRequiredError,
    StrategyRulerInvalidError,
)
from app.models.simulation import InitializeCampaignRequest, PlayerRulerRequest
from strategy_contracts.scenario import (
    LeaderSetup,
    PlayerRulerCustomization,
    StrategyScenario,
)

MIN_RULER_TRAITS = 2
MAX_RULER_TRAITS = 3
MIN_RULER_AMBITIONS = 1
MAX_RULER_AMBITIONS = 2
STATE_KEY = "strategy"
FACTION_STATE_KEY = "player_faction_id"
INITIALIZE_OPERATION_PREFIX = "init:"


def require_playable_faction(document: StrategyScenario, faction_id: str | None) -> str:
    playable_ids = {faction.id for faction in document.factions if faction.is_playable}
    if faction_id is None or faction_id not in playable_ids:
        raise StrategyFactionRequiredError()
    return faction_id


def derive_ruler(
    document: StrategyScenario,
    faction_id: str,
    player_ruler: PlayerRulerCustomization | None = None,
) -> PlayerRulerRequest:
    if player_ruler is not None:
        return PlayerRulerRequest(
            name=player_ruler.name,
            epithet=player_ruler.epithet,
            portrait_url=player_ruler.portrait_url,
            trait_ids=player_ruler.trait_ids[:MAX_RULER_TRAITS],
            ambition_ids=player_ruler.ambition_ids[:MAX_RULER_AMBITIONS],
            backstory=player_ruler.backstory,
        )
    leader = _leader_of(document, faction_id)
    if len(leader.trait_ids) < MIN_RULER_TRAITS:
        raise StrategyRulerInvalidError(
            f"{leader.name} needs at least {MIN_RULER_TRAITS} traits to rule"
        )
    if not leader.ambition_ids:
        raise StrategyRulerInvalidError(f"{leader.name} needs an ambition to rule")
    return PlayerRulerRequest(
        name=leader.name,
        trait_ids=leader.trait_ids[:MAX_RULER_TRAITS],
        ambition_ids=leader.ambition_ids[:MAX_RULER_AMBITIONS],
        backstory=leader.history,
    )


def _leader_of(document: StrategyScenario, faction_id: str) -> LeaderSetup:
    faction = next(item for item in document.factions if item.id == faction_id)
    for leader in document.leaders:
        if leader.id == faction.leader_id:
            return leader
    raise StrategyRulerInvalidError("This faction has no leader to rule")


def build_initialize_request(
    playthrough_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    document: StrategyScenario,
    faction_id: str,
    player_ruler: PlayerRulerCustomization | None = None,
) -> InitializeCampaignRequest:
    return InitializeCampaignRequest(
        playthrough_id=playthrough_id,
        owner_user_id=owner_user_id,
        operation_id=f"{INITIALIZE_OPERATION_PREFIX}{playthrough_id}",
        scenario=document,
        ruler=derive_ruler(document, faction_id, player_ruler),
        player_faction_id=faction_id,
    )
