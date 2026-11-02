from collections.abc import Sequence

from app.engine.negotiation import player_faction_id
from app.models.world_diplomacy import PrisonerKind
from app.models.world_events import EventLogEntry, PendingJudgment
from app.models.world_internal import UprisingStage
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.judgment import JudgmentSubjectKind
from strategy_contracts.scenario import StrategyScenario

TRIGGER_CAPTIVE = "captive_held"
TRIGGER_HOSTAGE = "hostage_at_mercy"
UPRISING_RESOLVING_EVENTS = frozenset({"uprising_crushed", "uprising_flipped"})
UPRISING_STAGE_EVENT = "uprising_stage_changed"
UPRISING_SUBJECT_COUNT = 3


def _pending(
    world: WorldState,
    scenario: StrategyScenario,
    kind: JudgmentSubjectKind,
    subject_id: str,
    accused_faction_id: FactionId,
    trigger_event: str,
) -> PendingJudgment:
    return PendingJudgment(
        subject_kind=kind,
        subject_id=subject_id,
        accused_faction_id=accused_faction_id,
        trigger_event=trigger_event,
        cooldown_until_turn=world.clock.turn + scenario.tuning.judgments.cooldown_turns,
    )


def _is_captive_open(
    world: WorldState, subject_id: str, sentence_ends_turn: int | None
) -> bool:
    if subject_id not in world.judgment_cooldowns:
        return True
    return sentence_ends_turn is not None and sentence_ends_turn <= world.clock.turn


def _prisoner_subjects(
    world: WorldState,
    scenario: StrategyScenario,
    player_id: FactionId,
    player_leader_id: str,
) -> list[PendingJudgment]:
    return [
        _pending(
            world,
            scenario,
            JudgmentSubjectKind.CAPTIVE,
            prisoner.id,
            prisoner.origin_faction_id,
            TRIGGER_CAPTIVE,
        )
        for prisoner in world.prisoners
        if prisoner.kind is PrisonerKind.CHARACTER
        and prisoner.held_by_id == player_id
        and prisoner.character_id != player_leader_id
        and _is_captive_open(world, prisoner.id, prisoner.sentence_ends_turn)
    ]


def _hostage_subjects(
    world: WorldState, scenario: StrategyScenario, player_id: FactionId
) -> list[PendingJudgment]:
    return [
        _pending(
            world,
            scenario,
            JudgmentSubjectKind.CAPTIVE,
            hostage.id,
            hostage.giver_id,
            TRIGGER_HOSTAGE,
        )
        for hostage in world.peace.hostages
        if hostage.holder_id == player_id
        and hostage.is_at_mercy
        and _is_captive_open(world, hostage.id, None)
    ]


def _is_trigger_event(event: EventLogEntry) -> bool:
    if event.kind in UPRISING_RESOLVING_EVENTS:
        return True
    is_stage_change = event.kind == UPRISING_STAGE_EVENT
    return (
        is_stage_change
        and bool(event.changes)
        and event.changes[-1].after == UprisingStage.ARMED.value
    )


def _event_governor_id(
    world: WorldState, event: EventLogEntry, player_id: FactionId
) -> str | None:
    subjects = event.cause.subject_ids
    if len(subjects) < UPRISING_SUBJECT_COUNT or subjects[1] != player_id:
        return None
    region = world.regions.get(subjects[2])
    if region is None or region.governor_id not in world.governors:
        return None
    return region.governor_id


def _governor_subjects(
    world: WorldState,
    scenario: StrategyScenario,
    player_id: FactionId,
    events: Sequence[EventLogEntry],
) -> list[PendingJudgment]:
    found: dict[str, PendingJudgment] = {}
    for event in filter(_is_trigger_event, events):
        governor_id = _event_governor_id(world, event, player_id)
        is_cooling = world.judgment_cooldowns.get(governor_id, 0) > world.clock.turn
        if governor_id is None or is_cooling or governor_id in found:
            continue
        found[governor_id] = _pending(
            world,
            scenario,
            JudgmentSubjectKind.GOVERNOR,
            governor_id,
            player_id,
            event.kind,
        )
    return list(found.values())


def eligible_subjects(
    world: WorldState, scenario: StrategyScenario, events: Sequence[EventLogEntry]
) -> list[PendingJudgment]:
    """Everyone the player may judge now, captives first, each group by id."""
    player_id = player_faction_id(world)
    player_leader_id = world.factions[player_id].leader_id or ""
    subjects = [
        *_prisoner_subjects(world, scenario, player_id, player_leader_id),
        *_hostage_subjects(world, scenario, player_id),
        *_governor_subjects(world, scenario, player_id, events),
    ]
    return sorted(subjects, key=lambda item: (item.subject_kind.value, item.subject_id))
