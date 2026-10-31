from app.engine.events.phase import EventsPhase
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.models.world_character import LeaderState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.conditions import (
    Comparison,
    ConditionMetric,
    ConditionOperator,
    ConditionScope,
)
from strategy_contracts.event_catalog import DISASTER_EVENTS
from strategy_contracts.events import (
    EffectKind,
    EffectSpec,
    EventChoice,
    EventDefinition,
    SeverityTier,
)
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scenario import StrategyScenario
from tests.models.builders import make_world as make_base_world

PLAYER = "house_carrow"
NPC = "house_ashford"
NPC_LEADER = "lord_ashford"
HARVEST_MONTH = 9
SEED = 42
FULL_PERCENT = 100


def make_disaster_world(month: int = HARVEST_MONTH) -> WorldState:
    world = make_base_world()
    world.events_ruleset = 2
    world.clock.start_month = month
    world.factions[NPC].leader_id = NPC_LEADER
    world.leaders[NPC_LEADER] = LeaderState(
        id=NPC_LEADER, name="Lord Ashford", faction_id=NPC, age=40
    )
    return world


def make_scenario(
    *, chance: int | None = FULL_PERCENT, extra_events: tuple[EventDefinition, ...] = ()
) -> StrategyScenario:
    scenario = load_three_crowns()
    scenario.tuning.event_frequency_percent = FULL_PERCENT
    disasters = (
        []
        if chance is None
        else [
            event.model_copy(update={"chance_percent": chance})
            for event in DISASTER_EVENTS
        ]
    )
    scenario.events = [*disasters, *extra_events]
    return scenario


def always_event(identifier: str, *, applies: bool) -> EventDefinition:
    trigger = Comparison(
        metric=ConditionMetric.TURN, operator=ConditionOperator.GTE, value=0
    )
    return EventDefinition(
        id=identifier,
        name="Always",
        subject_kind=ConditionScope.FACTION,
        cause_key=identifier,
        tiers=[SeverityTier(level=1, trigger=trigger)],
        choices=[
            EventChoice(id="one", label_hint="one", effects=[]),
            EventChoice(id="two", label_hint="two", effects=[]),
        ],
        neglect_effects=[EffectSpec(kind=EffectKind.UNREST, amount=1)],
        applies_to_npcs=applies,
    )


def run_events(
    world: WorldState, scenario: StrategyScenario
) -> tuple[WorldState, list[EventLogEntry]]:
    context = PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(SEED, world.clock.turn, "events"),
        resolved_outcomes={},
        recorded_answers={},
    )
    result = EventsPhase().run(world, context)
    return result.world, result.events


def pending_ids(world: WorldState) -> set[str]:
    return {pending.template_id for pending in world.pending_events}


def npc_events(events: list[EventLogEntry]) -> list[EventLogEntry]:
    return [event for event in events if event.kind == "npc_event_resolved"]
