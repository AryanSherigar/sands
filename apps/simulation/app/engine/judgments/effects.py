from app.engine.coalitions.ledger import record_atrocity
from app.engine.diplomacy.events import diplomacy_event
from app.engine.diplomacy.prisoners import (
    PRISONER_EXECUTED,
    find_prisoner,
    free_prisoner,
    handle_prisoner,
)
from app.engine.diplomacy.reputation import shift_standing
from app.engine.judgments.constants import (
    BASE_MERCY_SCORE,
    BASE_OPINION,
    JUDGMENT_CAUSE_CRUELTY,
    JUDGMENT_CAUSE_MERCY,
    JUDGMENT_OPINION_FADE_PER_TURN,
    MEMORY_KIND_PREFIX,
    MEMORY_WEIGHT,
    NUANCE_MERCY_SCORE,
    NUANCE_OPINION,
    WITNESS_GOVERNOR_SHIFT,
)
from app.engine.negotiation import player_faction_id
from app.engine.negotiation_memory import record_memory
from app.engine.opinion import shift_opinion
from app.engine.peace.hostages import find_hostage, harm_hostage, release_hostage
from app.engine.pressure.captivity import rally_after_execution
from app.models.orders import HandlePrisonerOrder
from app.models.world_character import GovernorState, LeaderState
from app.models.world_diplomacy import PrisonerState
from app.models.world_events import EventLogEntry, PendingJudgment
from app.models.world_state import WorldState
from strategy_contracts.judgment import (
    JudgmentNuance,
    JudgmentOutcome,
    JudgmentSubjectKind,
    JudgmentVerdict,
)
from strategy_contracts.scenario import StrategyScenario

JUDGMENT_PRONOUNCED = "judgment_pronounced"
MAX_PERCENT = 100


def _clamp(value: int) -> int:
    return min(MAX_PERCENT, max(-MAX_PERCENT, value))


def is_subject_present(world: WorldState, pending: PendingJudgment) -> bool:
    if pending.subject_kind is JudgmentSubjectKind.GOVERNOR:
        return pending.subject_id in world.governors
    return (
        find_prisoner(world, pending.subject_id) is not None
        or find_hostage(world, pending.subject_id) is not None
    )


def _execute_prisoner(
    world: WorldState,
    scenario: StrategyScenario,
    prisoner: PrisonerState,
    nuance: JudgmentNuance | None,
) -> list[EventLogEntry]:
    cost = scenario.tuning.peace.atrocity_reputation_cost
    is_quiet = nuance is JudgmentNuance.QUIETLY
    world.prisoners = [item for item in world.prisoners if item.id != prisoner.id]
    shift_standing(
        world.factions[prisoner.held_by_id], -(cost // 2 if is_quiet else cost), 0
    )
    if not is_quiet:
        record_atrocity(world, prisoner.held_by_id)
    if nuance is JudgmentNuance.PUBLICLY:
        record_atrocity(world, prisoner.held_by_id)
    rally_after_execution(world, scenario.tuning.peace, prisoner)
    return [
        diplomacy_event(
            PRISONER_EXECUTED,
            [prisoner.id, prisoner.held_by_id, prisoner.origin_faction_id],
        )
    ]


def _handle_prisoner_verdict(
    world: WorldState,
    scenario: StrategyScenario,
    prisoner: PrisonerState,
    outcome: JudgmentOutcome,
) -> list[EventLogEntry]:
    verdict, nuance = outcome.verdict, outcome.nuance
    if verdict is JudgmentVerdict.EXECUTE:
        return _execute_prisoner(world, scenario, prisoner, nuance)
    if verdict is JudgmentVerdict.EXILE:
        free_prisoner(world, prisoner)
    if verdict is JudgmentVerdict.RELEASE:
        action = "ransom" if nuance is JudgmentNuance.WITH_FINE else "release"
        order = HandlePrisonerOrder(
            faction_id=prisoner.held_by_id, prisoner_id=prisoner.id, action=action
        )
        return handle_prisoner(world, scenario, order)
    if nuance is JudgmentNuance.FOR_A_TERM:
        prisoner.sentence_ends_turn = (
            world.clock.turn + scenario.tuning.judgments.sentence_turns
        )
    return []


def _handle_hostage_verdict(
    world: WorldState,
    scenario: StrategyScenario,
    hostage_id: str,
    outcome: JudgmentOutcome,
) -> list[EventLogEntry]:
    if outcome.verdict in (JudgmentVerdict.RELEASE, JudgmentVerdict.EXILE):
        return release_hostage(world, hostage_id)
    if outcome.verdict is not JudgmentVerdict.EXECUTE:
        return []
    hostage = find_hostage(world, hostage_id)
    assert hostage is not None
    events = harm_hostage(world, scenario, hostage_id, hostage.holder_id)
    if outcome.nuance is JudgmentNuance.PUBLICLY:
        record_atrocity(world, hostage.holder_id)
    return events


def _handle_captive(
    world: WorldState,
    scenario: StrategyScenario,
    pending: PendingJudgment,
    outcome: JudgmentOutcome,
) -> list[EventLogEntry]:
    prisoner = find_prisoner(world, pending.subject_id)
    if prisoner is not None:
        return _handle_prisoner_verdict(world, scenario, prisoner, outcome)
    return _handle_hostage_verdict(world, scenario, pending.subject_id, outcome)


def _remove_governor(world: WorldState, governor: GovernorState) -> None:
    del world.governors[governor.id]
    region = world.regions.get(governor.region_id)
    if region is not None and region.governor_id == governor.id:
        region.governor_id = None


def _handle_governor(
    world: WorldState,
    scenario: StrategyScenario,
    pending: PendingJudgment,
    outcome: JudgmentOutcome,
) -> None:
    if outcome.verdict is not JudgmentVerdict.RELEASE:
        _remove_governor(world, world.governors[pending.subject_id])
    if outcome.nuance is JudgmentNuance.WITH_FINE:
        fine = scenario.tuning.peace.ransom_gold_per_character
        world.factions[player_faction_id(world)].treasury += fine


def opinion_value(outcome: JudgmentOutcome) -> int:
    nuance = outcome.nuance
    return BASE_OPINION[outcome.verdict] + (NUANCE_OPINION[nuance] if nuance else 0)


def mercy_value(outcome: JudgmentOutcome) -> int:
    nuance = outcome.nuance
    return BASE_MERCY_SCORE[outcome.verdict] + NUANCE_MERCY_SCORE.get(nuance, 0)


def _accused_leader(world: WorldState, pending: PendingJudgment) -> LeaderState | None:
    leader_id = world.factions[pending.accused_faction_id].leader_id
    return world.leaders.get(leader_id) if leader_id is not None else None


def _shift_accused_leader(
    world: WorldState, pending: PendingJudgment, outcome: JudgmentOutcome
) -> None:
    leader = _accused_leader(world, pending)
    if leader is None:
        return
    player_id = player_faction_id(world)
    value = opinion_value(outcome)
    cause = JUDGMENT_CAUSE_MERCY if value >= 0 else JUDGMENT_CAUSE_CRUELTY
    shift_opinion(
        world,
        pending.accused_faction_id,
        player_id,
        cause,
        value,
        JUDGMENT_OPINION_FADE_PER_TURN,
    )
    leader.beliefs.mercy_score = _clamp(
        leader.beliefs.mercy_score + mercy_value(outcome)
    )
    record_memory(
        leader,
        f"{MEMORY_KIND_PREFIX}{outcome.verdict.value}",
        MEMORY_WEIGHT,
        world.factions[player_id].leader_id,
        world.clock.turn,
    )


def _shift_witness_governors(
    world: WorldState, pending: PendingJudgment, verdict: JudgmentVerdict
) -> None:
    player_id = player_faction_id(world)
    shift = WITNESS_GOVERNOR_SHIFT[verdict]
    for governor in world.governors.values():
        region = world.regions.get(governor.region_id)
        is_witness = (
            governor.id != pending.subject_id
            and region is not None
            and region.owner_id == player_id
        )
        if is_witness:
            governor.opinion_of_ruler = _clamp(governor.opinion_of_ruler + shift)


def _record_profile(world: WorldState, verdict: JudgmentVerdict) -> None:
    if verdict is JudgmentVerdict.RELEASE:
        world.player_profile.mercy_acts += 1
    if verdict is JudgmentVerdict.EXECUTE:
        world.player_profile.cruelty_acts += 1


def apply_judgment(
    world: WorldState,
    scenario: StrategyScenario,
    pending: PendingJudgment,
    outcome: JudgmentOutcome,
) -> list[EventLogEntry]:
    """Apply a pronounced verdict; a subject that is already gone changes nothing."""
    if not is_subject_present(world, pending):
        return []
    if pending.subject_kind is JudgmentSubjectKind.GOVERNOR:
        events: list[EventLogEntry] = []
        _handle_governor(world, scenario, pending, outcome)
        _shift_witness_governors(world, pending, outcome.verdict)
    else:
        events = _handle_captive(world, scenario, pending, outcome)
        _shift_accused_leader(world, pending, outcome)
    _record_profile(world, outcome.verdict)
    subjects = [pending.subject_id, pending.accused_faction_id, outcome.verdict.value]
    return [*events, diplomacy_event(JUDGMENT_PRONOUNCED, subjects)]
