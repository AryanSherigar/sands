from app.engine.battles.state import (
    ExchangeRun,
    contingent_armies,
    fighting_contingents,
)
from app.engine.coalitions.ledger import record_atrocity
from app.engine.economy.armies import remove_army
from app.engine.outrage.effects import denies_quarter
from app.models.world_battle import BattleContingent, BattleSide, ContingentStatus
from app.models.world_character import CommanderStatus
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType


def _capture_id(run: ExchangeRun, contingent: BattleContingent) -> str:
    return f"{run.battle.id}:{contingent.faction_id}:{run.world.clock.turn}:{run.battle.total_exchanges + 1}"


def _capture_commander(
    run: ExchangeRun, army_id: str, held_by: str, capture_id: str
) -> None:
    army = run.world.armies[army_id]
    commander = run.world.commanders.get(army.commander_id or "")
    if commander is None:
        return
    commander.status = CommanderStatus.CAPTURED
    commander.army_id = None
    prisoner = PrisonerState(
        id=f"{capture_id}:commander:{commander.id}",
        held_by_id=held_by,
        origin_faction_id=army.owner_id,
        kind=PrisonerKind.CHARACTER,
        character_id=commander.id,
    )
    if all(existing.id != prisoner.id for existing in run.world.prisoners):
        run.world.prisoners.append(prisoner)


def _capture_troops(
    run: ExchangeRun, contingent: BattleContingent, held_by: str, capture_id: str
) -> None:
    armies = contingent_armies(run.world, contingent)
    troops = {
        troop_type: sum(army.troops.get(troop_type, 0) for army in armies)
        for troop_type in TroopType
    }
    troops = {troop_type: count for troop_type, count in troops.items() if count}
    if troops:
        prisoner = PrisonerState(
            id=f"{capture_id}:troops",
            held_by_id=held_by,
            origin_faction_id=contingent.faction_id,
            kind=PrisonerKind.TROOPS,
            troop_count=sum(troops.values()),
            origin_battle_id=run.battle.id,
            troops_by_type=troops,
        )
        if all(existing.id != prisoner.id for existing in run.world.prisoners):
            run.world.prisoners.append(prisoner)


def _slaughter_contingent(
    run: ExchangeRun, contingent: BattleContingent, killer_id: str
) -> None:
    for army in contingent_armies(run.world, contingent):
        run.accounting[army.id].combat_losses = {
            troop_type: count for troop_type, count in army.troops.items() if count
        }
        commander = run.world.commanders.get(army.commander_id or "")
        if commander is not None:
            commander.status = CommanderStatus.DEAD
            commander.army_id = None
        remove_army(run.world, army.id)
    record_atrocity(run.world, killer_id)
    contingent.status = ContingentStatus.SURRENDERED
    contingent.deployments = {}


def _capture_contingent(run: ExchangeRun, contingent: BattleContingent) -> None:
    held_by = (
        run.battle.defender_lead_faction_id
        if contingent.side == BattleSide.ATTACKER
        else run.battle.attacker_lead_faction_id
    )
    if denies_quarter(run.world, run.scenario, held_by):
        _slaughter_contingent(run, contingent, held_by)
        return
    capture_id = _capture_id(run, contingent)
    _capture_troops(run, contingent, held_by, capture_id)
    armies = contingent_armies(run.world, contingent)
    for army in armies:
        run.accounting[army.id].captives = {
            troop_type: count for troop_type, count in army.troops.items() if count
        }
        _capture_commander(run, army.id, held_by, capture_id)
        remove_army(run.world, army.id)
    contingent.status = ContingentStatus.SURRENDERED
    contingent.deployments = {}


def resolve_surrenders(
    run: ExchangeRun, faction_ids: set[str], withdrawing: set[str]
) -> None:
    """Opposing whole-side surrender disengages; partial surrenders use fixed lead captors."""
    active = fighting_contingents(run.battle)
    still_fighting = [
        contingent
        for contingent in active
        if contingent.faction_id not in faction_ids | withdrawing
    ]
    for faction_id in sorted(faction_ids):
        contingent = run.battle.contingents[faction_id]
        if not any(opponent.side != contingent.side for opponent in still_fighting):
            contingent.status = ContingentStatus.WITHDRAWN
            contingent.deployments = {}
            continue
        _capture_contingent(run, contingent)
