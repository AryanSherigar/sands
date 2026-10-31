from app.engine.pressure.wars import side_score
from app.models.world_diplomacy import WarState
from app.models.world_state import WorldState
from strategy_contracts.limits import MAX_CESSION_OPTIONS
from strategy_contracts.peace import PeaceTier
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import (
    CessionOption,
    PeaceBrief,
    PeaceTierOption,
    WarStanding,
)

STANDING_MARGIN = 10


def _standing(edge_for_player: int) -> WarStanding:
    if edge_for_player >= STANDING_MARGIN:
        return WarStanding.TRAILING
    if edge_for_player <= -STANDING_MARGIN:
        return WarStanding.LEADING
    return WarStanding.EVEN


def _tier_options(scenario: StrategyScenario) -> list[PeaceTierOption]:
    peace = scenario.tuning.peace
    guarantor_from = list(PeaceTier).index(peace.guarantor_required_from)
    return [
        PeaceTierOption(
            tier=tier,
            turns=peace.tier_turns[tier],
            needs_guarantor=index >= guarantor_from,
        )
        for index, tier in enumerate(PeaceTier)
    ]


def _faction_name(scenario: StrategyScenario, faction_id: str) -> str:
    setup = next((item for item in scenario.factions if item.id == faction_id), None)
    return faction_id if setup is None else setup.name


def _regions_of(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> list[CessionOption]:
    names = {region.id: region.name for region in scenario.map.regions}
    owned = [
        region_id
        for region_id, region in sorted(world.regions.items())
        if region.owner_id == faction_id
    ]
    return [
        CessionOption(region_id=region_id, name=names.get(region_id, region_id))
        for region_id in owned[:MAX_CESSION_OPTIONS]
    ]


def build_peace_brief(
    world: WorldState,
    scenario: StrategyScenario,
    player_id: str,
    counterpart_id: str,
    war: WarState | None,
) -> PeaceBrief:
    edge = (
        0
        if war is None
        else side_score(war, player_id) - side_score(war, counterpart_id)
    )
    return PeaceBrief(
        player_faction_id=player_id,
        player_faction_name=_faction_name(scenario, player_id),
        counterpart_faction_id=counterpart_id,
        counterpart_faction_name=_faction_name(scenario, counterpart_id),
        standing=_standing(edge),
        tiers=_tier_options(scenario),
        player_regions=_regions_of(world, scenario, player_id),
        counterpart_regions=_regions_of(world, scenario, counterpart_id),
    )
