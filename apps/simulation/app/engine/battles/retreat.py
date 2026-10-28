from collections.abc import Iterable
from dataclasses import dataclass

from app.engine.battles.deployment import allocate_largest_remainder
from app.engine.battles.morale import weighted_attribute
from app.engine.battles.state import (
    PERCENT,
    ExchangeRun,
    RetreatProposal,
    contingent_armies,
    exchange_rng,
    fighting_contingents,
    troop_count,
)
from app.engine.economy.arithmetic import ceil_division, clamp
from app.engine.movement.costs import route_base_cost
from app.engine.movement.map_index import build_map_index
from app.models.world_battle import BattleContingent, BattleState, ContingentStatus
from app.models.world_state import WorldState
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.scenario import StrategyScenario


@dataclass(frozen=True)
class RetreatDecision:
    contingent: BattleContingent
    candidates: tuple[str, ...]
    is_rout: bool
    has_escaped: bool
    pursuit_divisor: int
    has_pursuers: bool


def _is_friendly(world: WorldState, faction_id: str, owner_id: str | None) -> bool:
    return owner_id == faction_id or any(
        {relation.faction_a, relation.faction_b} == {faction_id, owner_id}
        and relation.status == RelationStatus.ALLIANCE
        for relation in world.relations
    )


def _is_hostile(world: WorldState, faction_id: str, owner_id: str) -> bool:
    return any(
        {relation.faction_a, relation.faction_b} == {faction_id, owner_id}
        and relation.status == RelationStatus.WAR
        for relation in world.relations
    )


def retreat_candidates(
    world: WorldState,
    battle: BattleState,
    contingent: BattleContingent,
    scenario: StrategyScenario,
) -> list[str]:
    """Return physically legal adjacent routes, ordered own/allied, movement cost, ID."""
    index = build_map_index(scenario.map)
    candidates = [
        region_id
        for region_id in sorted(index.neighbors.get(battle.region_id, ()))
        if _is_safe_destination(world, contingent.faction_id, region_id)
    ]
    return sorted(
        candidates,
        key=lambda region_id: (
            world.regions[region_id].owner_id != contingent.faction_id,
            route_base_cost(
                index, scenario.tuning.movement, battle.region_id, region_id
            ),
            region_id,
        ),
    )


def _is_safe_destination(world: WorldState, faction_id: str, region_id: str) -> bool:
    region = world.regions.get(region_id)
    if (
        region is None
        or region.occupation is not None
        or not _is_friendly(world, faction_id, region.owner_id)
    ):
        return False
    return not any(
        army.location_id == region_id and _is_hostile(world, faction_id, army.owner_id)
        for army in world.armies.values()
    )


def cavalry_share(world: WorldState, contingents: Iterable[BattleContingent]) -> int:
    armies = [
        army
        for contingent in contingents
        for army in contingent_armies(world, contingent)
    ]
    troops = sum(sum(army.troops.values()) for army in armies)
    return (
        PERCENT
        * sum(army.troops.get(TroopType.CAVALRY, 0) for army in armies)
        // max(1, troops)
    )


def _opponents(
    run: ExchangeRun, contingent: BattleContingent
) -> list[BattleContingent]:
    return [
        opponent
        for opponent in fighting_contingents(run.battle)
        if opponent.side != contingent.side and troop_count(run.world, opponent)
    ]


def _enemy_morale(run: ExchangeRun, opponents: list[BattleContingent]) -> int:
    total = sum(troop_count(run.world, opponent) for opponent in opponents)
    return sum(
        troop_count(run.world, opponent)
        * weighted_attribute(run.world, opponent, "morale")
        for opponent in opponents
    ) // max(1, total)


def _escape_score(
    run: ExchangeRun,
    contingent: BattleContingent,
    opponents: list[BattleContingent],
    is_rout: bool,
) -> int:
    tuning = run.scenario.tuning.battle
    difference = weighted_attribute(run.world, contingent, "morale") - _enemy_morale(
        run, opponents
    )
    cavalry_difference = cavalry_share(run.world, [contingent]) - cavalry_share(
        run.world, opponents
    )
    score = (
        tuning.escape_base_percent
        + difference // tuning.escape_morale_divisor
        + tuning.escape_cavalry_factor * cavalry_difference // PERCENT
        + tuning.terrain_escape_bonus[run.battle.terrain]
    )
    score = clamp(score, tuning.escape_min_percent, tuning.escape_max_percent)
    if is_rout:
        score = clamp(
            score - tuning.rout_escape_penalty,
            tuning.escape_min_percent,
            tuning.escape_max_percent,
        )
    return score


def _has_escaped(
    run: ExchangeRun,
    contingent: BattleContingent,
    opponents: list[BattleContingent],
    is_rout: bool,
    stage: str,
) -> bool:
    rng = exchange_rng(run, contingent.faction_id, "escape", stage)
    return rng.roll(PERCENT) < _escape_score(run, contingent, opponents, is_rout)


def _decide(
    run: ExchangeRun, contingent: BattleContingent, stage: str, leaving: set[str]
) -> RetreatDecision:
    candidates = tuple(
        retreat_candidates(run.world, run.battle, contingent, run.scenario)
    )
    opponents = _opponents(run, contingent)
    is_rout = contingent.status == ContingentStatus.ROUTED
    has_escaped = bool(candidates) and _has_escaped(
        run, contingent, opponents, is_rout, stage
    )
    pursuers = [
        opponent for opponent in opponents if opponent.faction_id not in leaving
    ]
    divisor = (
        1
        if cavalry_share(run.world, pursuers)
        else run.scenario.tuning.battle.no_cavalry_pursuit_divisor
    )
    return RetreatDecision(
        contingent, candidates, is_rout, has_escaped, divisor, bool(pursuers)
    )


def _apply_pursuit(run: ExchangeRun, decision: RetreatDecision) -> None:
    contingent = decision.contingent
    if not decision.has_pursuers or contingent.has_pursuit_resolved:
        return
    tuning = run.scenario.tuning.battle
    rate = (
        tuning.rout_pursuit_loss_percent
        if decision.is_rout
        else tuning.pursuit_loss_percent
    )
    armies = contingent_armies(run.world, contingent)
    for troop_type in TroopType:
        weights = {army.id: army.troops.get(troop_type, 0) for army in armies}
        losses = min(
            sum(weights.values()),
            ceil_division(
                sum(weights.values()) * rate, PERCENT * decision.pursuit_divisor
            ),
        )
        _apply_pursuit_cells(
            run, troop_type, allocate_largest_remainder(losses, weights)
        )
    contingent.has_pursuit_resolved = True


def _apply_pursuit_cells(
    run: ExchangeRun, troop_type: TroopType, losses: dict[str, int]
) -> None:
    for army_id, count in sorted(losses.items()):
        if count:
            run.world.armies[army_id].troops[troop_type] -= count
            run.accounting[army_id].pursuit_losses[troop_type] = count


def _apply_retreat(run: ExchangeRun, decision: RetreatDecision) -> None:
    contingent = decision.contingent
    if not decision.has_escaped:
        return
    _apply_pursuit(run, decision)
    contingent.status = ContingentStatus.WITHDRAWN
    contingent.retreat_destination_id = decision.candidates[0]
    armies = contingent_armies(run.world, contingent)
    for army in armies:
        army.location_id = decision.candidates[0]
        army.march = None
        army.order = None
        army.morale = max(1, army.morale)
    run.retreat_proposals.append(
        RetreatProposal(
            faction_id=contingent.faction_id,
            army_ids=[army.id for army in armies],
            candidate_region_ids=list(decision.candidates),
            destination_id=decision.candidates[0],
            is_rout=decision.is_rout,
        )
    )


def resolve_retreats(run: ExchangeRun, faction_ids: set[str], stage: str) -> None:
    """Freeze every escape and pursuit opportunity before applying simultaneous departures."""
    leaving = set(faction_ids) | run.excluded_attackers
    decisions = [
        _decide(run, run.battle.contingents[faction_id], stage, leaving)
        for faction_id in sorted(faction_ids)
    ]
    for decision in decisions:
        _apply_retreat(run, decision)
