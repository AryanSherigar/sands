from dataclasses import dataclass

from app.models.world_state import WorldState
from strategy_contracts.coalition import CoalitionTuning
from strategy_contracts.ids import FactionId
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario


@dataclass(frozen=True)
class ThreatReading:
    value: int
    conquest: int
    treaty_breaking: int
    atrocity: int
    balance: int


def conquest_threat(
    world: WorldState, tuning: CoalitionTuning, faction_id: FactionId
) -> int:
    oldest = world.clock.turn - tuning.conquest_window_turns
    gained = sum(
        record.wealth
        for record in world.coalition.conquests
        if record.faction_id == faction_id and record.turn > oldest
    )
    return gained // tuning.conquest_wealth_divisor


def treaty_breaking_threat(
    world: WorldState, tuning: CoalitionTuning, faction_id: FactionId
) -> int:
    is_oathbreaker = any(mark.faction_id == faction_id for mark in world.oathbreakers)
    groundless_wars = sum(
        1
        for war in world.wars
        if war.attacker_id == faction_id and war.ground_kind is None
    )
    return (
        tuning.oathbreaker_threat if is_oathbreaker else 0
    ) + groundless_wars * tuning.no_ground_war_threat


def faction_power(world: WorldState, faction_id: FactionId) -> int:
    wealth = sum(
        region.wealth
        for region in world.regions.values()
        if region.owner_id == faction_id
    )
    troops = sum(
        sum(army.troops.values())
        for army in world.armies.values()
        if army.owner_id == faction_id
    )
    return wealth + troops


def balance_threat(
    world: WorldState, tuning: CoalitionTuning, faction_id: FactionId
) -> int:
    total = sum(
        faction_power(world, other.id)
        for other in world.factions.values()
        if not other.is_destroyed
    )
    share = FULL_SHARE_PERCENT * faction_power(world, faction_id) // max(1, total)
    excess = max(0, share - tuning.balance_fair_share_percent)
    return excess * tuning.balance_weight_percent // FULL_SHARE_PERCENT


def compute_threat(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> ThreatReading:
    tuning = scenario.tuning.coalition
    conquest = conquest_threat(world, tuning, faction_id)
    treaty = treaty_breaking_threat(world, tuning, faction_id)
    atrocity = world.coalition.atrocities.get(faction_id, 0) * tuning.atrocity_threat
    balance = balance_threat(world, tuning, faction_id)
    value = min(FULL_SHARE_PERCENT, conquest + treaty + atrocity + balance)
    return ThreatReading(value, conquest, treaty, atrocity, balance)
