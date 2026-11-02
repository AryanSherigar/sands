from dataclasses import dataclass
from enum import Enum

from app.engine.opinion import opinion_of
from app.engine.pressure.captivity import captive_drain, captive_points
from app.engine.pressure.wars import find_war
from app.engine.pressure.will import compute_will
from app.engine.trait_axes import axis_totals
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_state import WorldState
from strategy_contracts.peace import PERCENT, PeaceTuning
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis


class RansomResponse(str, Enum):
    ACCEPT = "accept"
    HAGGLE = "haggle"
    REFUSE = "refuse"


@dataclass(frozen=True)
class RansomVerdict:
    response: RansomResponse
    counter_gold: int = 0


def _kind_percent(
    world: WorldState, tuning: PeaceTuning, prisoner: PrisonerState
) -> int:
    if prisoner.kind is PrisonerKind.TROOPS:
        return min(
            tuning.ransom_troop_percent_cap, captive_points(world, prisoner, tuning)
        )
    leader_id = world.factions[prisoner.origin_faction_id].leader_id
    if prisoner.character_id == leader_id:
        return tuning.ransom_ruler_percent
    return tuning.ransom_character_percent


def _home_pressure_percent(
    world: WorldState, scenario: StrategyScenario, prisoner: PrisonerState
) -> int:
    tuning = scenario.tuning.peace
    origin_id = prisoner.origin_faction_id
    stability = PERCENT - world.factions[origin_id].stability
    percent = stability * tuning.ransom_stability_weight // PERCENT
    percent += captive_drain(world, scenario, origin_id) * tuning.ransom_captive_weight
    if find_war(world, prisoner.held_by_id, origin_id) is not None:
        will = compute_will(world, scenario, origin_id).value
        percent += (PERCENT - will) * tuning.ransom_will_weight // PERCENT
    return percent


def _ruler_percent(
    world: WorldState, scenario: StrategyScenario, prisoner: PrisonerState
) -> int:
    tuning = scenario.tuning.peace
    origin = world.factions[prisoner.origin_faction_id]
    leader = world.leaders.get(origin.leader_id or "")
    if leader is None:
        return 0
    totals = axis_totals(leader, scenario)
    kind = totals[TraitAxis.HONOR] + totals[TraitAxis.TRUST]
    hard = totals[TraitAxis.CRUELTY] + totals[TraitAxis.PRIDE]
    holder_leader_id = world.factions[prisoner.held_by_id].leader_id
    warmth = opinion_of(leader, holder_leader_id) // tuning.ransom_opinion_divisor
    return tuning.ransom_trait_percent_step * (kind - hard) + warmth


def ransom_willingness(
    world: WorldState, scenario: StrategyScenario, prisoner: PrisonerState
) -> int:
    """Percent of the asking price the origin is ready to pay for this captive."""
    tuning = scenario.tuning.peace
    return (
        tuning.ransom_base_percent
        + _kind_percent(world, tuning, prisoner)
        + _home_pressure_percent(world, scenario, prisoner)
        + _ruler_percent(world, scenario, prisoner)
    )


def _accept_line(
    world: WorldState, scenario: StrategyScenario, prisoner: PrisonerState
) -> int:
    origin = world.factions[prisoner.origin_faction_id]
    leader = world.leaders.get(origin.leader_id or "")
    greed = axis_totals(leader, scenario)[TraitAxis.GREED] if leader else 0
    return PERCENT + max(0, greed) * scenario.tuning.peace.ransom_greed_accept_step


def ransom_verdict(
    world: WorldState,
    scenario: StrategyScenario,
    prisoner: PrisonerState,
    price: int,
) -> RansomVerdict:
    tuning = scenario.tuning.peace
    willingness = ransom_willingness(world, scenario, prisoner)
    treasury = world.factions[prisoner.origin_faction_id].treasury
    if willingness >= _accept_line(world, scenario, prisoner) and treasury >= price:
        return RansomVerdict(RansomResponse.ACCEPT)
    counter = min(price * willingness // PERCENT, treasury)
    is_open = willingness >= tuning.ransom_haggle_floor_percent and counter > 0
    if not is_open:
        return RansomVerdict(RansomResponse.REFUSE)
    return RansomVerdict(RansomResponse.HAGGLE, min(counter, price))
