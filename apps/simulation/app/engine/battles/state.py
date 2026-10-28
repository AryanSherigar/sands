from dataclasses import dataclass, field

from app.engine.rng import DeterministicRng, derive_rng
from app.models.base import WorldModel
from app.models.battle_command import AcceptedCommand
from app.models.battle_intelligence import (
    BattleIntent,
    ReconReport,
    ScoutCapture,
    ScoutMission,
)
from app.models.world_army import ArmyState
from app.models.world_battle import (
    BattleContingent,
    BattleSide,
    BattleState,
    ContingentStatus,
    ExchangeReceipt,
    LossAccounting,
)
from app.models.world_character import CommanderState
from app.models.world_diplomacy import PrisonerState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from pydantic import Field
from strategy_contracts.enums import TroopType
from strategy_contracts.scenario import StrategyScenario

PERCENT = 100
FIGHTING_STATUSES = frozenset((ContingentStatus.FIGHTING, ContingentStatus.ROUTED))


class RetreatProposal(WorldModel):
    faction_id: str
    army_ids: list[str]
    candidate_region_ids: list[str]
    destination_id: str
    is_rout: bool


class BattleDelta(WorldModel):
    """Battle-owned replacements only; the wave reducer owns counters and event sequences.

    Retreat destinations in army_updates are provisional. The reducer arbitrates
    retreat_proposals across battles before applying the selected destinations.
    """

    battle: BattleState
    army_updates: dict[str, ArmyState] = Field(default_factory=dict)
    removed_army_ids: list[str] = Field(default_factory=list)
    commander_updates: dict[str, CommanderState] = Field(default_factory=dict)
    prisoners: list[PrisonerState] = Field(default_factory=list)
    command_updates: list[AcceptedCommand] = Field(default_factory=list)
    recon_reports: dict[str, ReconReport] = Field(default_factory=dict)
    scout_missions: dict[str, ScoutMission] = Field(default_factory=dict)
    scout_captures: dict[str, ScoutCapture] = Field(default_factory=dict)
    battle_intents: dict[str, BattleIntent] = Field(default_factory=dict)
    retreat_proposals: list[RetreatProposal] = Field(default_factory=list)


class ExchangeResult(WorldModel):
    """Owns a deep-copied proposed world; use delta when reducing a frozen multi-battle wave."""

    world: WorldState
    delta: BattleDelta
    events: list[EventLogEntry]
    receipt: ExchangeReceipt
    is_terminal: bool


@dataclass
class ExchangeRun:
    world: WorldState
    battle: BattleState
    scenario: StrategyScenario
    accounting: dict[str, LossAccounting]
    excluded_attackers: set[str] = field(default_factory=set)
    retreat_proposals: list[RetreatProposal] = field(default_factory=list)


def exchange_rng(run: ExchangeRun, *keys: str) -> DeterministicRng:
    return derive_rng(
        run.world.rng.seed,
        run.world.clock.turn,
        "battles",
        run.battle.id,
        run.battle.total_exchanges + 1,
        *keys,
    )


def contingent_armies(
    world: WorldState, contingent: BattleContingent
) -> list[ArmyState]:
    return [
        world.armies[army_id]
        for army_id in sorted(contingent.army_ids)
        if army_id in world.armies
    ]


def troop_count(world: WorldState, contingent: BattleContingent) -> int:
    return sum(
        sum(army.troops.values()) for army in contingent_armies(world, contingent)
    )


def side_contingents(battle: BattleState, side: BattleSide) -> list[BattleContingent]:
    return [
        battle.contingents[key]
        for key in sorted(battle.contingents)
        if battle.contingents[key].side == side
    ]


def fighting_contingents(battle: BattleState) -> list[BattleContingent]:
    return [
        battle.contingents[key]
        for key in sorted(battle.contingents)
        if battle.contingents[key].status in FIGHTING_STATUSES
    ]


def troop_cells(
    world: WorldState, contingent: BattleContingent
) -> dict[tuple[str, TroopType], int]:
    return {
        (army.id, troop_type): count
        for army in contingent_armies(world, contingent)
        for troop_type, count in sorted(army.troops.items())
        if count
    }
