from app.engine.battles.events import exchange_events
from app.engine.battles.state import BattleDelta, ExchangeResult, ExchangeRun
from app.engine.hashing import world_hash
from app.models.battle_command import AcceptedCommand, CommandStatus
from app.models.world_battle import BattleStatus, ExchangeReceipt, LossAccounting
from app.models.world_character import CommanderState
from app.models.world_state import WorldState


def _finish_accounting(run: ExchangeRun) -> list[LossAccounting]:
    rows: list[LossAccounting] = []
    for army_id in sorted(run.accounting):
        row = run.accounting[army_id]
        army = run.world.armies.get(army_id)
        row.survivors = dict(army.troops) if army else {}
        rows.append(LossAccounting.model_validate(row.model_dump()))
    return rows


def _finish_commands(run: ExchangeRun, commands: list[AcceptedCommand]) -> None:
    for accepted in commands:
        accepted.status = CommandStatus.APPLIED
        accepted.applied_turn = run.world.clock.turn
        accepted.applied_wave = run.battle.exchanges_used
    replacements = {command.id: command for command in commands}
    run.world.accepted_commands = [
        replacements.get(command.id, command) for command in run.world.accepted_commands
    ]


def build_delta(
    before: WorldState, run: ExchangeRun, commands: list[AcceptedCommand]
) -> BattleDelta:
    """Emit only battle-owned updates, so independent worlds cannot overwrite each other."""
    delta = BattleDelta(battle=run.battle.model_copy(deep=True))
    delta.army_updates = {
        army_id: run.world.armies[army_id].model_copy(deep=True)
        for army_id in sorted(run.accounting)
        if army_id in run.world.armies
    }
    delta.removed_army_ids = sorted(run.accounting.keys() - run.world.armies.keys())
    delta.commander_updates = _commander_updates(before, run)
    existing_prisoners = {prisoner.id for prisoner in before.prisoners}
    delta.prisoners = [
        prisoner.model_copy(deep=True)
        for prisoner in run.world.prisoners
        if prisoner.id not in existing_prisoners
    ]
    delta.command_updates = [command.model_copy(deep=True) for command in commands]
    delta.battle_intents = {
        identity: intent.model_copy(deep=True)
        for identity, intent in sorted(run.world.battle_intents.items())
        if intent.battle_id == run.battle.id
        and before.battle_intents.get(identity) != intent
    }
    delta.retreat_proposals = [
        proposal.model_copy(deep=True) for proposal in run.retreat_proposals
    ]
    _intelligence_delta(delta, before, run)
    return delta


def _commander_updates(
    before: WorldState, run: ExchangeRun
) -> dict[str, CommanderState]:
    commanders = {
        army.commander_id
        for army_id, army in before.armies.items()
        if army_id in run.accounting and army.commander_id
    }
    return {
        identity: run.world.commanders[identity].model_copy(deep=True)
        for identity in sorted(commanders)
        if identity in run.world.commanders
    }


def exchange_result(
    before: WorldState, run: ExchangeRun, commands: list[AcceptedCommand]
) -> ExchangeResult:
    accounting = _finish_accounting(run)
    _finish_commands(run, commands)
    receipt = ExchangeReceipt(
        battle_id=run.battle.id,
        campaign_turn=run.world.clock.turn,
        exchange_index=run.battle.exchanges_used,
        total_exchange=run.battle.total_exchanges,
        input_hash=world_hash(before),
        output_hash=world_hash(run.world),
        rule_version=run.scenario.tuning.battle.rule_version,
        command_ids=[command.id for command in commands],
        intent_ids=sorted(
            contingent.intent_id
            for contingent in run.battle.contingents.values()
            if contingent.intent_id
        ),
        accounting=accounting,
        outcome=run.battle.outcome,
    )
    return ExchangeResult(
        world=run.world,
        delta=build_delta(before, run, commands),
        events=exchange_events(run),
        receipt=receipt,
        is_terminal=run.battle.status == BattleStatus.RESOLVED,
    )


def _intelligence_delta(
    delta: BattleDelta, before: WorldState, run: ExchangeRun
) -> None:
    delta.recon_reports = {
        identity: report.model_copy(deep=True)
        for identity, report in sorted(run.world.recon_reports.items())
        if report.battle_id == run.battle.id
        and before.recon_reports.get(identity) != report
    }
    delta.scout_missions = {
        identity: mission.model_copy(deep=True)
        for identity, mission in sorted(run.world.scout_missions.items())
        if mission.battle_id == run.battle.id
        and before.scout_missions.get(identity) != mission
    }
    delta.scout_captures = {
        identity: capture.model_copy(deep=True)
        for identity, capture in sorted(run.world.scout_captures.items())
        if capture.battle_id == run.battle.id
        and before.scout_captures.get(identity) != capture
    }
