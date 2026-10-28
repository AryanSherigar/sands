from app.engine.commands.ledger import PENDING_STATUSES
from app.engine.economy.manpower import faction_manpower
from app.engine.movement.knowledge import visible_regions
from app.engine.movement.map_index import MapIndex, build_map_index
from app.engine.negotiation import active_pacts
from app.models.api_battle import CampaignWorldView
from app.models.api_world_view import (
    ArmyView,
    IntRange,
    OwnFactionView,
    PactView,
    QueuedOrderView,
    RegionView,
    RivalView,
    Visibility,
)
from app.models.world_internal import is_rebel_faction
from app.models.world_state import WorldState
from app.services.alliance_projection import project_alliances, project_calls
from app.services.campaign_state import player_faction, project_state
from app.services.coalition_projection import project_coalitions, project_own_threat
from app.services.event_projection import project_event_memories, project_pending_events
from app.services.peace_projection import (
    project_hostages,
    project_mediations,
    project_truces,
)
from app.services.pressure_projection import project_own_pressure, project_rumors
from app.services.uprising_projection import project_uprisings
from app.services.vassal_projection import (
    project_pending_demands,
    project_vassalages,
)
from strategy_contracts.enums import RelationStatus
from strategy_contracts.scenario import StrategyScenario

ROUGH_RANGE_STEP = 50


def own_faction(world: WorldState, faction_id: str) -> OwnFactionView:
    faction = world.factions[faction_id]
    return OwnFactionView(
        id=faction.id,
        leader_id=faction.leader_id,
        treasury=faction.treasury,
        manpower=faction_manpower(world, faction_id),
        stability=faction.stability,
        war_exhaustion=faction.war_exhaustion,
        reputation=faction.reputation,
        tax_rate=faction.tax_rate,
        loans=faction.loans,
    )


def project_region(
    world: WorldState,
    identity: str,
    faction_id: str,
    index: MapIndex,
    visible: frozenset[str],
) -> RegionView:
    region = world.regions[identity]
    intel = world.factions[faction_id].intel.get(identity)
    is_visible = identity in visible
    view = RegionView(
        region_id=identity,
        owner_id=None,
        terrain=index.terrain[identity],
        visibility=Visibility.VISIBLE if is_visible else Visibility.FOGGED,
    )
    if intel is not None:
        view.owner_id = intel.owner_id
        view.last_seen_turn = intel.last_seen_turn
        view.garrison_estimate = IntRange(
            low=intel.garrison_low, high=intel.garrison_high
        )
    if is_visible:
        view.owner_id = region.owner_id
        view.last_seen_turn = world.clock.turn
    if region.owner_id == faction_id:
        view.detail = region.model_copy(deep=True)
    return view


def own_armies(world: WorldState, faction_id: str) -> list[ArmyView]:
    return [
        ArmyView(
            army_id=army.id,
            owner_id=army.owner_id,
            location_id=army.location_id,
            troops=army.troops,
        )
        for _, army in sorted(world.armies.items())
        if army.owner_id == faction_id
    ]


def queued_order_views(world: WorldState, faction_id: str) -> list[QueuedOrderView]:
    is_planning = world.progress.phase is None
    return [
        QueuedOrderView(
            id=command.id,
            order=command.command,
            cost=command.reserved_cost,
            queued_turn=command.accepted_turn,
            is_cancellable=is_planning and command.accepted_turn == world.clock.turn,
        )
        for command in world.accepted_commands
        if command.faction_id == faction_id
        and command.battle_id is None
        and command.status in PENDING_STATUSES
    ]


def _rough_range(value: int) -> IntRange:
    low = max(0, value) // ROUGH_RANGE_STEP * ROUGH_RANGE_STEP
    return IntRange(low=low, high=low + ROUGH_RANGE_STEP)


def _relation_status(
    world: WorldState, faction_a: str, faction_b: str
) -> RelationStatus:
    pair = tuple(sorted((faction_a, faction_b)))
    for relation in world.relations:
        if (relation.faction_a, relation.faction_b) == pair:
            return relation.status
    return RelationStatus.PEACE


def project_rivals(
    world: WorldState, scenario: StrategyScenario, faction_id: str
) -> list[RivalView]:
    names = {item.id: item.name for item in scenario.factions}
    return [
        RivalView(
            faction_id=identity,
            name=names.get(identity, identity),
            leader_name=world.leaders[faction.leader_id].name
            if faction.leader_id in world.leaders
            else None,
            relation=_relation_status(world, faction_id, identity),
            treasury_range=_rough_range(faction.treasury),
            manpower_range=_rough_range(faction_manpower(world, identity)),
        )
        for identity, faction in sorted(world.factions.items())
        if identity != faction_id
        and not faction.is_destroyed
        and not is_rebel_faction(identity)
    ]


def project_pacts(world: WorldState) -> list[PactView]:
    return [
        PactView(
            commitment_id=commitment.id,
            faction_a=commitment.term.faction_a,
            faction_b=commitment.term.faction_b,
            start_turn=commitment.start_turn,
            end_turn=commitment.end_turn,
        )
        for commitment in active_pacts(world)
    ]


def project_world(
    world: WorldState, scenario: StrategyScenario, version: int, digest: str
) -> CampaignWorldView:
    faction_id = player_faction(world)
    index = build_map_index(scenario.map)
    visible = visible_regions(world, faction_id, index)
    state = project_state(world, scenario, version, digest)
    return CampaignWorldView(
        **state.model_dump(),
        clock=world.clock,
        ending=world.ending,
        ruler=world.ruler,
        my_faction=own_faction(world, faction_id),
        armies=own_armies(world, faction_id),
        queued_orders=queued_order_views(world, faction_id),
        pending_events=project_pending_events(world, scenario, faction_id),
        event_memories=project_event_memories(world, scenario),
        rivals=project_rivals(world, scenario, faction_id),
        pacts=project_pacts(world),
        uprisings=project_uprisings(world, scenario, faction_id),
        own_pressure=project_own_pressure(world, scenario, faction_id),
        rumors=project_rumors(world, faction_id),
        truces=project_truces(world, faction_id),
        own_hostages=project_hostages(world, faction_id),
        open_mediations=project_mediations(world, faction_id),
        alliances=project_alliances(world, faction_id),
        pending_calls=project_calls(world, faction_id),
        vassalages=project_vassalages(world, faction_id),
        pending_demands=project_pending_demands(world, faction_id),
        coalitions=project_coalitions(world, faction_id),
        own_threat=project_own_threat(world, scenario, faction_id),
        regions=[
            project_region(world, identity, faction_id, index, visible)
            for identity in sorted(world.regions)
        ],
    )
