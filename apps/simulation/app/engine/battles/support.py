from app.engine.battles.captures import refresh_penalties, resolve_capture_decision
from app.engine.battles.deception import (
    activate_deception,
    false_hint,
    has_deception,
    preparation_hint,
)
from app.engine.battles.reconnaissance import (
    ReconResolution,
    intelligence_id,
    resolve_recon,
)
from app.engine.battles.state import ExchangeRun
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import (
    AcceptedCommand,
    CaptureDecisionCommand,
    DeceiveCommand,
    ReconCommand,
)
from app.models.battle_intelligence import ScoutMission


def _mission(run: ExchangeRun, accepted: AcceptedCommand) -> ScoutMission:
    command = accepted.command
    if not isinstance(command, ReconCommand):
        raise SimulationServiceError("unsupported mission command")
    contingent = run.battle.contingents[accepted.faction_id]
    hint = preparation_hint(contingent)
    if has_deception(run.battle, contingent):
        hint = false_hint(hint)
    return ScoutMission(
        id=intelligence_id("scout_mission", run.battle.id, accepted.id),
        battle_id=run.battle.id,
        observer_faction_id=accepted.faction_id,
        subject_faction_id=command.subject_faction_id,
        target=command.target,
        execution_turn=run.world.clock.turn,
        execution_wave=run.battle.exchanges_used + 1,
        briefing_hint=hint,
    )


def _resolve_missions(
    run: ExchangeRun, commands: list[AcceptedCommand]
) -> list[ReconResolution]:
    results = []
    frozen = run.world.model_copy(deep=True)
    frozen_battle = next(
        battle for battle in frozen.battles if battle.id == run.battle.id
    )
    missions = [
        _mission(run, accepted)
        for accepted in commands
        if isinstance(accepted.command, ReconCommand)
    ]
    for mission in missions:
        result = resolve_recon(frozen, mission, run.scenario)
        results.append(result)
        if result.has_consumed_deception:
            frozen_battle.contingents[
                mission.subject_faction_id
            ].deception_expires_exchange = None
            run.battle.contingents[
                mission.subject_faction_id
            ].deception_expires_exchange = None
    return results


def _store_mission(run: ExchangeRun, result: ReconResolution) -> None:
    mission = result.mission
    run.world.scout_missions[mission.id] = mission
    run.battle.mission_ids.append(mission.id)
    if result.report is not None:
        run.world.recon_reports[result.report.id] = result.report
        run.battle.report_ids.append(result.report.id)
    if result.capture is not None:
        run.world.scout_captures[result.capture.id] = result.capture
        run.battle.capture_ids.append(result.capture.id)


def _capture_decision(run: ExchangeRun, accepted: AcceptedCommand) -> None:
    command = accepted.command
    if not isinstance(command, CaptureDecisionCommand):
        return
    capture = run.world.scout_captures.get(command.capture_id)
    if capture is None or capture.battle_id != run.battle.id:
        raise SimulationServiceError("capture decision is unavailable")
    result = resolve_capture_decision(
        run.world,
        command.capture_id,
        accepted.faction_id,
        command.decision,
        run.scenario,
    )
    run.world.scout_captures[result.capture.id] = result.capture
    if result.report is not None:
        run.world.recon_reports[result.report.id] = result.report
        run.battle.report_ids.append(result.report.id)


def resolve_support(run: ExchangeRun, commands: list[AcceptedCommand]) -> None:
    refresh_penalties(run.world, run.battle, run.scenario)
    for accepted in commands:
        if isinstance(accepted.command, DeceiveCommand):
            activate_deception(run.battle, run.battle.contingents[accepted.faction_id])
    missions = _resolve_missions(run, commands)
    for accepted in commands:
        _capture_decision(run, accepted)
    for result in missions:
        _store_mission(run, result)
    refresh_penalties(run.world, run.battle, run.scenario)
