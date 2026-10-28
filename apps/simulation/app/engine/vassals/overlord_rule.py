from app.engine.pressure.wars import side_score, wars_of
from app.engine.trait_axes import axis_totals
from app.engine.vassals.demands import issue_demand, validate_demand_from_vassal
from app.engine.vassals.registry import granted_share, vassal_term, vassals_of
from app.exceptions.command_exceptions import CommandError
from app.models.orders import DemandFromVassalOrder
from app.models.world_diplomacy import CommitmentState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis
from strategy_contracts.vassal import DemandKind


def _is_losing_a_war(world: WorldState, faction_id: FactionId) -> bool:
    for war in wars_of(world, faction_id):
        own = side_score(war, faction_id)
        other = war.war_score_attacker + war.war_score_defender - own
        if own < other:
            return True
    return False


def _shortfall_percent(
    world: WorldState, scenario: StrategyScenario, overlord_id: FactionId
) -> int:
    ceiling = scenario.tuning.vassal.overlord_strain_treasury
    treasury = world.factions[overlord_id].treasury
    gap = max(0, ceiling - treasury)
    return gap * FULL_SHARE_PERCENT // max(ceiling, 1)


def _is_strained(
    world: WorldState, scenario: StrategyScenario, overlord_id: FactionId
) -> bool:
    return _shortfall_percent(world, scenario, overlord_id) > 0 or _is_losing_a_war(
        world, overlord_id
    )


def _greed_scale(
    world: WorldState, scenario: StrategyScenario, overlord_id: FactionId
) -> int:
    leader = world.leaders[world.factions[overlord_id].leader_id]
    totals = axis_totals(leader, scenario)
    leaning = (
        totals[TraitAxis.GREED] + totals[TraitAxis.PRIDE] - totals[TraitAxis.CAUTION]
    )
    weighted = FULL_SHARE_PERCENT + scenario.tuning.vassal.axis_weight * leaning
    return max(0, weighted)


def _asked_share(
    world: WorldState,
    scenario: StrategyScenario,
    commitment: CommitmentState,
) -> int:
    overlord_id = vassal_term(commitment).overlord_id
    ceiling = scenario.tuning.vassal.overlord_demand_max_excess_percent
    raw = max(1, _shortfall_percent(world, scenario, overlord_id))
    scaled = raw * _greed_scale(world, scenario, overlord_id) // FULL_SHARE_PERCENT
    excess = min(ceiling, max(1, scaled))
    granted = granted_share(commitment, DemandKind.TRIBUTE)
    return min(FULL_SHARE_PERCENT, granted + excess)


def _order_for(
    world: WorldState, scenario: StrategyScenario, commitment: CommitmentState
) -> DemandFromVassalOrder:
    return DemandFromVassalOrder(
        faction_id=vassal_term(commitment).overlord_id,
        vassalage_id=commitment.id,
        demand_kind=DemandKind.TRIBUTE,
        amount=_asked_share(world, scenario, commitment),
    )


def _richest_first(
    world: WorldState, commitments: list[CommitmentState]
) -> list[CommitmentState]:
    return sorted(
        commitments,
        key=lambda item: (
            -world.factions[vassal_term(item).vassal_id].treasury,
            item.id,
        ),
    )


def _is_active_npc(world: WorldState, faction_id: FactionId) -> bool:
    faction = world.factions[faction_id]
    return not (faction.is_player or faction.is_destroyed) and faction.leader_id in (
        world.leaders
    )


def _demand_from_richest(
    world: WorldState, scenario: StrategyScenario, overlord_id: FactionId
) -> list[EventLogEntry]:
    for commitment in _richest_first(world, vassals_of(world, overlord_id)):
        order = _order_for(world, scenario, commitment)
        try:
            validate_demand_from_vassal(world, scenario, order)
        except CommandError:
            continue
        return issue_demand(world, scenario, order)
    return []


def npc_overlord_demands(
    world: WorldState, scenario: StrategyScenario
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for overlord_id in sorted(world.factions):
        is_candidate = _is_active_npc(world, overlord_id) and _is_strained(
            world, scenario, overlord_id
        )
        if is_candidate:
            events += _demand_from_richest(world, scenario, overlord_id)
    return events
