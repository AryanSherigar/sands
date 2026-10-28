from app.exceptions.command_exceptions import CampaignProgressError
from app.models.battle_command import AcceptedCommand, Command
from app.models.world_events import MAX_CAMPAIGN_WAVES, PhaseName
from app.models.world_state import UPRISING_LIFECYCLE_RULESET, WorldState

URGENT_KINDS = frozenset(("set_pay", "take_loan", "declare_default"))
MOVEMENT_KINDS = frozenset(("move_army", "attack", "halt_army"))
DIPLOMACY_KINDS = frozenset(
    (
        "declare_war",
        "diplomatic_play",
        "call_negotiation",
        "fabricate_claim",
        "send_envoy",
        "handle_prisoner",
        "mediate",
        "answer_call",
        "denounce_alliance",
        "demand_from_vassal",
        "answer_demand",
        "grant_consent",
        "release_vassal",
        "annex_vassal",
    )
)
DIPLOMACY_SLOT_FIELDS = {
    "handle_prisoner": "prisoner_id",
    "mediate": "war_id",
    "answer_call": "call_id",
    "denounce_alliance": "alliance_id",
    "answer_demand": "demand_id",
    "release_vassal": "vassalage_id",
    "annex_vassal": "vassalage_id",
    "demand_from_vassal": "vassalage_id",
}
ANSWER_EVENT_KIND = "answer_event"


def require_window(
    world: WorldState,
    expected_turn: int,
    expected_wave: int,
    *,
    can_choose_control: bool = False,
) -> None:
    if world.clock.turn != expected_turn:
        raise CampaignProgressError("stale campaign turn", "stale_cursor")
    if (
        world.progress.phase != PhaseName.BATTLES
        or world.progress.waiting_reason
        not in (
            ("awaiting_commands", "awaiting_battle_decision")
            if can_choose_control
            else ("awaiting_commands",)
        )
    ):
        raise CampaignProgressError(
            "battle command window is closed", "invalid_lifecycle"
        )
    if (
        expected_wave != world.progress.completed_waves + 1
        or not 1 <= expected_wave <= MAX_CAMPAIGN_WAVES
    ):
        raise CampaignProgressError("stale campaign wave", "stale_cursor")


def is_urgent(world: WorldState, command: Command) -> bool:
    if command.kind == "resolve_uprising":
        return not is_uprising_queued(world)
    return command.kind in URGENT_KINDS


def is_uprising_queued(world: WorldState) -> bool:
    return world.internal_ruleset >= UPRISING_LIFECYCLE_RULESET


def execution_boundary(world: WorldState, command: Command) -> tuple[int, int]:
    if getattr(command, "battle_id", None) is not None:
        return world.clock.turn, world.progress.completed_waves + 1
    if world.progress.phase is None or is_urgent(world, command):
        return world.clock.turn, 0
    return world.clock.turn + 1, 0


def owning_phase(accepted: AcceptedCommand) -> PhaseName:
    if accepted.battle_id is not None:
        return PhaseName.BATTLES
    if accepted.command.kind in MOVEMENT_KINDS:
        return PhaseName.MOVEMENT
    if accepted.command.kind in DIPLOMACY_KINDS:
        return PhaseName.DIPLOMACY
    if accepted.command.kind == ANSWER_EVENT_KIND:
        return PhaseName.EVENTS
    if accepted.command.kind == "resolve_uprising":
        return PhaseName.INTERNAL
    return PhaseName.ECONOMY


def command_slot(command: Command) -> tuple[str, str]:
    if command.kind in ("take_command", "delegate_battle"):
        return "battle_control", ""
    if command.kind == "resolve_uprising":
        return "uprising", command.uprising_id
    if command.kind == ANSWER_EVENT_KIND:
        return ANSWER_EVENT_KIND, command.event_id
    if command.kind in ("set_plan", "withdraw", "surrender"):
        return "instruction", ""
    if command.kind in MOVEMENT_KINDS:
        return "movement", command.army_id
    if command.kind in DIPLOMACY_SLOT_FIELDS:
        return command.kind, getattr(command, DIPLOMACY_SLOT_FIELDS[command.kind])
    if command.kind in DIPLOMACY_KINDS:
        return command.kind, command.target_faction_id
    subject = (
        getattr(command, "capture_id", None)
        or getattr(command, "army_id", None)
        or getattr(command, "region_id", "")
    )
    return command.kind, subject
