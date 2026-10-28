from dataclasses import dataclass

from app.engine.ai.standing import FULL_PERCENT, known_power_ratio
from app.engine.opinion import opinion_of
from app.engine.trait_axes import axis_totals
from app.engine.vassals.overreach import (
    HALF_DIVISOR,
    affected_region_ids,
    excess_percent_of,
)
from app.models.world_state import WorldState
from app.models.world_vassal import DemandState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.traits import TraitAxis
from strategy_contracts.vassal import DemandReply, VassalTuning

REPLY_ORDER = (
    DemandReply.ACCEPT,
    DemandReply.COUNTER,
    DemandReply.REFUSE,
    DemandReply.REFUSE_STRONGLY,
    DemandReply.REBEL,
)


@dataclass(frozen=True)
class ReplyInputs:
    temperament: int
    cunning: int
    opinion: int
    power_percent: int
    mean_unrest: int
    excess_percent: int
    has_army: bool


@dataclass(frozen=True)
class ReplyChoice:
    reply: DemandReply
    reason_key: str


def _mean_unrest(world: WorldState, demand: DemandState) -> int:
    regions = affected_region_ids(world, demand)
    if not regions:
        return 0
    return sum(world.regions[item].unrest for item in regions) // len(regions)


def gather_inputs(
    world: WorldState, scenario: StrategyScenario, demand: DemandState
) -> ReplyInputs:
    tuning = scenario.tuning.vassal
    leader = world.leaders[world.factions[demand.vassal_id].leader_id]
    totals = axis_totals(leader, scenario)
    leaning = (
        totals[TraitAxis.HONOR]
        + totals[TraitAxis.TRUST]
        + totals[TraitAxis.CAUTION]
        - totals[TraitAxis.PRIDE]
        - totals[TraitAxis.AGGRESSION]
    )
    overlord_leader_id = world.factions[demand.overlord_id].leader_id
    return ReplyInputs(
        temperament=tuning.axis_weight * leaning,
        cunning=tuning.axis_weight * totals[TraitAxis.CUNNING],
        opinion=opinion_of(leader, overlord_leader_id) // tuning.opinion_divisor,
        power_percent=known_power_ratio(
            world, scenario, demand.vassal_id, demand.overlord_id
        ),
        mean_unrest=_mean_unrest(world, demand),
        excess_percent=excess_percent_of(demand, tuning),
        has_army=any(
            army.owner_id == demand.vassal_id for army in world.armies.values()
        ),
    )


def _soft_reply_terms(
    inputs: ReplyInputs, tuning: VassalTuning, excess: int, strength: int
) -> dict[DemandReply, dict[str, int]]:
    temperament = inputs.temperament
    spread = abs(inputs.excess_percent - tuning.counter_target_percent)
    return {
        DemandReply.ACCEPT: {
            "base": tuning.accept_base,
            "temperament": temperament,
            "opinion": inputs.opinion,
            "excess": -excess,
            "strength": -strength,
        },
        DemandReply.COUNTER: {
            "base": tuning.counter_base,
            "cunning": inputs.cunning,
            "excess": -(spread // tuning.counter_spread_divisor),
        },
        DemandReply.REFUSE: {
            "base": tuning.refuse_base,
            "temperament": -(temperament // HALF_DIVISOR),
            "excess": excess // HALF_DIVISOR,
            "strength": strength,
        },
    }


def reply_terms(
    inputs: ReplyInputs, tuning: VassalTuning
) -> dict[DemandReply, dict[str, int]]:
    excess = inputs.excess_percent // tuning.excess_divisor
    strength = (inputs.power_percent - FULL_PERCENT) // tuning.strength_divisor
    terms = _soft_reply_terms(inputs, tuning, excess, strength)
    terms.update(_hard_reply_terms(inputs, tuning, excess, strength))
    return terms


def _hard_reply_terms(
    inputs: ReplyInputs, tuning: VassalTuning, excess: int, strength: int
) -> dict[DemandReply, dict[str, int]]:
    terms: dict[DemandReply, dict[str, int]] = {}
    if inputs.excess_percent >= tuning.strong_min_excess_percent:
        terms[DemandReply.REFUSE_STRONGLY] = {
            "base": tuning.strong_base,
            "temperament": -inputs.temperament,
            "excess": excess,
            "strength": strength,
        }
    can_rebel = (
        inputs.power_percent >= tuning.rebel_min_power_percent
        and inputs.mean_unrest >= tuning.rebel_min_unrest
        and inputs.has_army
    )
    if can_rebel:
        terms[DemandReply.REBEL] = {
            "base": tuning.rebel_base,
            "temperament": -inputs.temperament,
            "unrest": inputs.mean_unrest // tuning.rebel_unrest_divisor,
            "excess": excess,
            "strength": strength,
        }
    return terms


def pick_best(scores: dict[DemandReply, int]) -> DemandReply:
    best: DemandReply | None = None
    for reply in REPLY_ORDER:
        if reply in scores and (best is None or scores[reply] > scores[best]):
            best = reply
    assert best is not None
    return best


def choose_reply(
    world: WorldState, scenario: StrategyScenario, demand: DemandState
) -> ReplyChoice:
    terms = reply_terms(gather_inputs(world, scenario, demand), scenario.tuning.vassal)
    reply = pick_best({key: sum(value.values()) for key, value in terms.items()})
    chosen = terms[reply]
    reason = max(sorted(chosen), key=lambda name: abs(chosen[name]))
    return ReplyChoice(reply, reason)
