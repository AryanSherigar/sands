from app.engine.alliances.answers import apply_answer, resolve_calls
from app.engine.alliances.denounce import denounce_alliance, expire_alliances
from app.engine.coalitions.phase import tick_coalitions
from app.engine.commands.ledger import due_commands
from app.engine.diplomacy.envoy import open_envoy
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.fabrication import start_forgery, tick_forgeries
from app.engine.diplomacy.grounds import expire_grounds
from app.engine.diplomacy.mediation import apply_mediation
from app.engine.diplomacy.plays import open_play, resolve_due_plays
from app.engine.diplomacy.prisoners import handle_prisoner
from app.engine.diplomacy.validation import validate_diplomacy_order
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.diplomacy.war_score import tally_war_scores
from app.engine.outrage.ledger import tick_outrage
from app.engine.peace.breach import tick_breach
from app.engine.peace.hostages import release_due_hostages
from app.engine.peace.truces import expire_truces
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.pressure.counters import update_stalemate
from app.engine.pressure.phase import tick_pressure
from app.engine.vassals.commands import (
    VASSAL_REFUNDED_REASONS,
    VassalOrder,
    apply_vassal_order,
    consume_used_consent,
)
from app.engine.vassals.phase import run_vassal_diplomacy, tick_vassals
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import AcceptedCommand, CommandStatus
from app.models.orders import (
    AnswerCallOrder,
    CallNegotiationOrder,
    DeclareWarOrder,
    DenounceAllianceOrder,
    DiplomaticPlayOrder,
    FabricateClaimOrder,
    HandlePrisonerOrder,
    MediateOrder,
    SendEnvoyOrder,
)
from app.models.world_events import EventLogEntry, PhaseName
from app.models.world_state import WorldState

REFUNDED_REASONS = frozenset(
    (
        "already_at_war",
        "unknown_prisoner",
        "not_holder",
        "cannot_pay",
        "no_exchange_counterpart",
        "unknown_war",
        "mediator_is_belligerent",
        "mediator_unavailable",
        "offer_exists",
        "peace_disabled",
        "unknown_call",
        "not_ally",
        "call_expired",
        "unknown_alliance",
        "not_member",
    )
)


def _fail(world: WorldState, command: AcceptedCommand, reason: str) -> None:
    command.status = CommandStatus.FAILED
    command.failure_reason = reason
    if reason in REFUNDED_REASONS | VASSAL_REFUNDED_REASONS:
        world.factions[command.faction_id].orders_remaining += command.reserved_cost


def _mark_applied(world: WorldState, command: AcceptedCommand) -> None:
    command.status = CommandStatus.APPLIED
    command.applied_turn = world.clock.turn
    command.applied_wave = world.progress.completed_waves


def _apply_core_order(
    world: WorldState, command: AcceptedCommand, context: PhaseContext
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    if isinstance(command.command, DeclareWarOrder):
        events = declare_war(world, context.scenario, command.command)
    elif isinstance(command.command, DiplomaticPlayOrder | CallNegotiationOrder):
        events = open_play(world, context.scenario, command.command)
    elif isinstance(command.command, SendEnvoyOrder):
        events = [open_envoy(world, command.command)]
    elif isinstance(command.command, MediateOrder):
        events = apply_mediation(world, context.scenario, command.command)
    elif isinstance(command.command, HandlePrisonerOrder):
        events = handle_prisoner(world, context.scenario, command.command)
    elif isinstance(command.command, AnswerCallOrder):
        events = apply_answer(world, context.scenario, command.command)
    elif isinstance(command.command, DenounceAllianceOrder):
        events = denounce_alliance(world, context.scenario, command.command)
    elif isinstance(command.command, FabricateClaimOrder):
        events = [start_forgery(world, context.scenario, command.command)]
    return events


def _apply_command(
    world: WorldState, command: AcceptedCommand, context: PhaseContext
) -> list[EventLogEntry]:
    try:
        validate_diplomacy_order(world, command.command, context.scenario)
    except CommandError as error:
        _fail(world, command, error.code)
        return []
    if isinstance(command.command, VassalOrder):
        events = apply_vassal_order(world, context.scenario, command.command)
    else:
        events = _apply_core_order(world, command, context)
    consume_used_consent(world, command.command)
    _mark_applied(world, command)
    return events


class DiplomacyPhase:
    name = PhaseName.DIPLOMACY

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        if not world.diplomacy_ruleset:
            return PhaseResult(world)
        events = resolve_due_plays(world, context.scenario)
        due = sorted(
            due_commands(world, self.name),
            key=lambda command: (command.faction_id, command.id),
        )
        for command in due:
            events += _apply_command(world, command, context)
        if world.alliance_ruleset:
            events += resolve_calls(world, context.scenario)
        events += run_vassal_diplomacy(world, context.scenario)
        return PhaseResult(world, events)


class TimePhase:
    name = PhaseName.TIME

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        if not world.diplomacy_ruleset:
            return PhaseResult(world)
        events = [
            diplomacy_event(
                "ground_expired",
                [ground.id, ground.holder_faction_id],
                phase=PhaseName.TIME,
            )
            for ground in expire_grounds(world, context.scenario)
        ]
        forged = tick_forgeries(world, context.scenario, context.rng)
        events += [
            event.model_copy(update={"phase": PhaseName.TIME}) for event in forged
        ]
        events += [
            diplomacy_event(
                "truce_expired",
                [truce.faction_a, truce.faction_b],
                phase=PhaseName.TIME,
            )
            for truce in expire_truces(world)
        ]
        events += expire_alliances(world)
        events += tick_vassals(world, context.scenario)
        events += [
            event.model_copy(update={"phase": PhaseName.TIME})
            for event in release_due_hostages(world)
        ]
        scores_before = {
            war.id: (war.war_score_attacker, war.war_score_defender)
            for war in world.wars
        }
        events += tally_war_scores(world, context.scenario)
        if world.pressure_ruleset:
            update_stalemate(world, scores_before)
            events += tick_pressure(world, context.scenario, context.rng)
        if world.peace_ruleset:
            events += tick_breach(world, context.scenario, context.rng)
        events += tick_coalitions(world, context.scenario)
        events += [
            event.model_copy(update={"phase": PhaseName.TIME})
            for event in tick_outrage(world, context.scenario)
        ]
        return PhaseResult(world, events)
