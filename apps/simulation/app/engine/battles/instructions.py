from collections.abc import Mapping, Sequence

from app.engine.battles.modifiers import validate_tactic
from app.engine.battles.retreat import resolve_retreats, retreat_candidates
from app.engine.battles.state import (
    FIGHTING_STATUSES,
    PERCENT,
    ExchangeRun,
    troop_count,
)
from app.engine.battles.surrender import resolve_surrenders
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import (
    AcceptedCommand,
    CaptureDecisionCommand,
    CommandStatus,
    CommitReservesCommand,
    DeceiveCommand,
    DelegateBattleCommand,
    ReconCommand,
    SetPlanCommand,
    SurrenderCommand,
    TakeCommandCommand,
    WithdrawCommand,
)
from app.models.battle_intelligence import BattleIntent
from app.models.world_battle import ContingentStatus


def eligible_commands(
    run: ExchangeRun, commands: Sequence[AcceptedCommand]
) -> list[AcceptedCommand]:
    selected = [
        command.model_copy(deep=True)
        for command in commands
        if command.battle_id == run.battle.id
        and command.execution_turn == run.world.clock.turn
        and command.execution_wave == run.battle.exchanges_used + 1
        and command.status == CommandStatus.ACCEPTED
    ]
    supported = (
        SetPlanCommand,
        CommitReservesCommand,
        ReconCommand,
        DeceiveCommand,
        CaptureDecisionCommand,
        WithdrawCommand,
        SurrenderCommand,
        TakeCommandCommand,
        DelegateBattleCommand,
    )
    if any(not isinstance(accepted.command, supported) for accepted in selected):
        raise SimulationServiceError("command requires battle support resolution")
    identities = [command.id for command in selected]
    if len(set(identities)) != len(identities):
        raise SimulationServiceError("duplicate exchange command")
    return sorted(selected, key=lambda command: (command.faction_id, command.id))


def _apply_plan(run: ExchangeRun, accepted: AcceptedCommand) -> None:
    contingent = run.battle.contingents[accepted.faction_id]
    command = accepted.command
    if not isinstance(command, SetPlanCommand):
        return
    validate_tactic(
        run.world, run.battle, contingent, command.plan, run.scenario.tuning.battle
    )
    if contingent.plan == command.plan:
        return
    contingent.plan = command.plan.model_copy(deep=True)
    contingent.has_committed_reserves = False
    total = troop_count(run.world, contingent)
    share = (
        PERCENT
        - run.scenario.tuning.battle.formation_reserve_percent[command.plan.formation]
    )
    contingent.desired_active = (
        max(
            1,
            min(total, run.scenario.tuning.battle.frontage[run.battle.terrain])
            * share
            // PERCENT,
        )
        if total
        else 0
    )


def apply_instructions(
    run: ExchangeRun, commands: list[AcceptedCommand]
) -> tuple[set[str], set[str]]:
    withdrawing: set[str] = set()
    surrendering: set[str] = set()
    ordered = sorted(
        commands, key=lambda accepted: not isinstance(accepted.command, SetPlanCommand)
    )
    for accepted in ordered:
        if isinstance(accepted.command, TakeCommandCommand):
            run.battle.control_mode = run.battle.control_mode.PLAYER
            continue
        if isinstance(accepted.command, DelegateBattleCommand):
            run.battle.control_mode = run.battle.control_mode.DELEGATED
            continue
        contingent = run.battle.contingents.get(accepted.faction_id)
        if (
            contingent is None
            or contingent.status not in FIGHTING_STATUSES
            or not troop_count(run.world, contingent)
        ):
            raise SimulationServiceError("command requires a fighting contingent")
        _apply_plan(run, accepted)
        if isinstance(accepted.command, CommitReservesCommand):
            contingent.has_committed_reserves = True
        if isinstance(accepted.command, WithdrawCommand):
            withdrawing.add(accepted.faction_id)
        if isinstance(accepted.command, SurrenderCommand):
            surrendering.add(accepted.faction_id)
    return withdrawing, surrendering


def activate_intents(
    run: ExchangeRun, recorded_intents: Mapping[str, BattleIntent]
) -> None:
    for identity in sorted(recorded_intents):
        intent = recorded_intents[identity]
        if (
            intent.battle_id != run.battle.id
            or intent.campaign_turn != run.world.clock.turn
        ):
            continue
        if (
            intent.activation_wave != run.battle.exchanges_used + 1
            or intent.activation_exchange != run.battle.total_exchanges + 1
        ):
            continue
        if intent.faction_id not in run.battle.contingents:
            continue
        run.world.battle_intents[intent.id] = intent.model_copy(deep=True)
        run.battle.contingents[intent.faction_id].intent_id = intent.id


def resolve_declarations(
    run: ExchangeRun, withdrawing: set[str], surrendering: set[str]
) -> None:
    routed = [
        contingent
        for contingent in run.battle.contingents.values()
        if contingent.status == ContingentStatus.ROUTED
    ]
    for contingent in routed:
        if retreat_candidates(run.world, run.battle, contingent, run.scenario):
            withdrawing.add(contingent.faction_id)
        else:
            surrendering.add(contingent.faction_id)
    run.excluded_attackers.update(withdrawing | surrendering)
    resolve_retreats(run, withdrawing - surrendering, "declaration")
    resolve_surrenders(run, surrendering, set())
