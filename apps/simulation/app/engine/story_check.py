from app.engine.ending_rules.streaks import advance_ending_streaks
from app.engine.endings import (
    GRADED_MINIMUM_RULESET,
    evaluate_default_endings,
    next_collapse_streak,
)
from app.engine.phases import PhaseContext, PhaseResult
from app.models.world_events import EndingState, EventCause, EventLogEntry, PhaseName
from app.models.world_state import WorldState


class StoryCheckPhase:
    name = PhaseName.STORY_CHECK

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        if not _should_check_endings(world, context):
            return PhaseResult(world)
        world.stability_collapse_turns = next_collapse_streak(world)
        if world.endings_ruleset >= GRADED_MINIMUM_RULESET:
            advance_ending_streaks(world, context.scenario)
        ending = evaluate_default_endings(world, context.scenario)
        if ending is None:
            return PhaseResult(world)
        world.ending = ending
        return PhaseResult(world, [_ending_reached(ending)])


def _should_check_endings(world: WorldState, context: PhaseContext) -> bool:
    return (
        world.endings_ruleset > 0
        and world.ending is None
        and context.scenario.is_using_default_endings
    )


def _ending_reached(ending: EndingState) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=PhaseName.STORY_CHECK,
        kind="ending_reached",
        is_major=True,
        cause=EventCause(
            summary_key=f"endings.{ending.ending_id}",
            subject_ids=[ending.ending_id],
            inputs=dict(ending.inputs),
        ),
    )
