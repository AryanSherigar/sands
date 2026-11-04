from app.engine.alliances.answers import apply_answer, resolve_calls
from app.engine.alliances.denounce import denounce_alliance, expire_alliances
from app.engine.coalitions.appease import apply_appease
from app.engine.coalitions.phase import tick_coalitions
from app.engine.commands.ledger import due_commands
from app.engine.diplomacy.envoy import open_envoy
from app.engine.diplomacy.espionage import bribe_envoy
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.fabrication import start_forgery, tick_forgeries
from app.engine.diplomacy.grounds import expire_grounds
from app.engine.diplomacy.mediation import apply_mediation
from app.engine.diplomacy.npc_captives import act_on_player_captives
from app.engine.diplomacy.npc_peace import apply_sue_peace
from app.engine.diplomacy.plays import open_play, resolve_due_plays
from app.engine.diplomacy.prisoners import execute_held_prisoners, handle_prisoner
from app.engine.diplomacy.validation import validate_diplomacy_order
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.diplomacy.war_score import tally_war_scores
from app.engine.outrage.ledger import tick_outrage
from app.engine.outrage.mobilize import apply_mobilize
from app.engine.peace.breach import tick_breach
from app.engine.peace.decisive_defeat import apply_decisive_defeats
from app.engine.peace.hostages import release_due_hostages
from app.engine.peace.truces import expire_truces
from app.engine.phases import PhaseContext, PhaseResult
from app.engine.pressure.captivity import is_captivity_active, tick_captivity
from app.engine.pressure.counters import update_stalemate
from app.engine.pressure.phase import tick_pressure
from app.engine.pressure.subsidies import (
    apply_cut_subsidy,
    apply_subsidize,
    pay_subsidies,
)
from app.engine.succession.phase import tick_succession
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
    AppeaseCoalitionOrder,
    BribeEnvoyOrder,
    CallNegotiationOrder,
    CutSubsidyOrder,
    DeclareWarOrder,
    DenounceAllianceOrder,
    DiplomaticPlayOrder,
    FabricateClaimOrder,
    HandlePrisonerOrder,
    MediateOrder,
    MobilizeOrder,
    SendEnvoyOrder,
    SubsidizeOrder,
    SuePeaceOrder,
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
        "pressure_disabled",
        "receiver_unavailable",
        "receiver_not_in_war",
        "payer_is_enemy",
        "bad_amount",
        "bad_duration",
        "subsidy_exists",
        "unknown_subsidy",
        "not_payer",
        "outrage_disabled",
        "not_at_war",
        "already_mobilized",
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


def _apply_resource_order(
    world: WorldState,
    order: SubsidizeOrder | CutSubsidyOrder | MobilizeOrder,
    context: PhaseContext,
) -> list[EventLogEntry]:
    if isinstance(order, SubsidizeOrder):
        return apply_subsidize(world, context.scenario, order)
    if isinstance(order, MobilizeOrder):
        return apply_mobilize(world, context.scenario, order)
    return apply_cut_subsidy(world, order)


def _apply_peace_order(
    world: WorldState,
    order: MediateOrder | SuePeaceOrder,
    context: PhaseContext,
) -> list[EventLogEntry]:
    if isinstance(order, MediateOrder):
        return apply_mediation(world, context.scenario, order)
    return apply_sue_peace(world, context.scenario, order)


def _apply_pact_order(
    world: WorldState,
    order: DenounceAllianceOrder | AppeaseCoalitionOrder,
    context: PhaseContext,
) -> list[EventLogEntry]:
    if isinstance(order, DenounceAllianceOrder):
        return denounce_alliance(world, context.scenario, order)
    return apply_appease(world, context.scenario, order)


def _apply_covert_order(
    world: WorldState,
    order: HandlePrisonerOrder | BribeEnvoyOrder,
    context: PhaseContext,
) -> list[EventLogEntry]:
    if isinstance(order, BribeEnvoyOrder):
        return bribe_envoy(world, context.scenario, order)
    return handle_prisoner(world, context.scenario, order)


def _apply_core_order(
    world: WorldState, command: AcceptedCommand, context: PhaseContext
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    if isinstance(command.command, DeclareWarOrder):
        events = declare_war(world, context.scenario, command.command)
    elif isinstance(command.command, DiplomaticPlayOrder | CallNegotiationOrder):
        events = open_play(world, context.scenario, command.command)
    elif isinstance(command.command, SendEnvoyOrder):
        events = [open_envoy(world, command.command, context.scenario, context.rng)]
    elif isinstance(command.command, MediateOrder | SuePeaceOrder):
        events = _apply_peace_order(world, command.command, context)
    elif isinstance(command.command, SubsidizeOrder | CutSubsidyOrder | MobilizeOrder):
        events = _apply_resource_order(world, command.command, context)
    elif isinstance(command.command, HandlePrisonerOrder | BribeEnvoyOrder):
        events = _apply_covert_order(world, command.command, context)
    elif isinstance(command.command, AnswerCallOrder):
        events = apply_answer(world, context.scenario, command.command)
    elif isinstance(command.command, DenounceAllianceOrder | AppeaseCoalitionOrder):
        events = _apply_pact_order(world, command.command, context)
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
            events += pay_subsidies(world)
            update_stalemate(world, scores_before)
            events += tick_pressure(world, context.scenario, context.rng)
        if world.peace_ruleset:
            events += tick_breach(world, context.scenario, context.rng)
            tick_captivity(world, context.scenario)
            events += [
                event.model_copy(update={"phase": PhaseName.TIME})
                for event in apply_decisive_defeats(world, context.scenario)
            ]
        events += tick_coalitions(world, context.scenario)
        events += [
            event.model_copy(update={"phase": PhaseName.TIME})
            for event in tick_outrage(world, context.scenario)
        ]
        events += [
            event.model_copy(update={"phase": PhaseName.TIME})
            for event in execute_held_prisoners(world, context.scenario)
        ]
        if is_captivity_active(world):
            events += [
                event.model_copy(update={"phase": PhaseName.TIME})
                for event in act_on_player_captives(world, context.scenario)
            ]
        events += tick_succession(world, context.scenario, context.rng)
        return PhaseResult(world, events)
