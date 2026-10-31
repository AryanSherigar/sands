from dataclasses import dataclass

from app.engine.conditions import read_metric
from app.engine.events.constants import (
    CHANCE_STREAM,
    FREQUENCY_ROLL_RANGE,
    MAX_NEW_EVENTS_PER_TURN,
)
from app.engine.events.memory import find_memory
from app.engine.events.tiers import tier_level
from app.engine.rng import DeterministicRng
from app.engine.subjects import Subject
from app.models.world_state import WorldState
from strategy_contracts.conditions import (
    SUBJECT_PLACEHOLDER,
    Comparison,
    ConditionMetric,
    ConditionOperator,
    ConditionScope,
    iter_comparisons,
    metric_scope,
)
from strategy_contracts.events import EventDefinition


@dataclass(frozen=True)
class Firing:
    template: EventDefinition
    subject: Subject
    tier: int


def escalated_tier(
    world: WorldState, template: EventDefinition, subject: Subject, faction_id: str
) -> int:
    memory = find_memory(world, template.id, subject.id)
    scar = memory.scar if memory is not None else 0
    last_tier = memory.last_tier if memory is not None else 0
    tier = tier_level(world, template, subject, scar=scar, faction_id=faction_id)
    return tier if tier > last_tier else 0


def _passes_gates(
    firing: Firing, rng: DeterministicRng, frequency_percent: int
) -> bool:
    template, subject = firing.template, firing.subject
    if (
        rng.fork(template.id, subject.id).roll(FREQUENCY_ROLL_RANGE)
        >= frequency_percent
    ):
        return False
    chance = rng.fork(template.id, subject.id, CHANCE_STREAM).roll(FREQUENCY_ROLL_RANGE)
    return chance < template.chance_percent


def gate_firings(
    firings: list[Firing], rng: DeterministicRng, frequency_percent: int
) -> list[Firing]:
    return [
        firing for firing in firings if _passes_gates(firing, rng, frequency_percent)
    ]


def cap_firings(firings: list[Firing]) -> list[Firing]:
    ranked = sorted(
        firings, key=lambda item: (-item.tier, item.template.id, item.subject.id)
    )
    return ranked[:MAX_NEW_EVENTS_PER_TURN]


def cause_inputs(world: WorldState, firing: Firing, faction_id: str) -> dict[str, int]:
    inputs: dict[str, int] = {}
    for metric in firing.template.cause_metrics:
        value = read_metric(
            world,
            _probe(firing.template, metric),
            faction_id=faction_id,
            subject=firing.subject,
        )
        if value is not None:
            inputs[metric.value] = value
    return inputs


def _probe(template: EventDefinition, metric: ConditionMetric) -> Comparison:
    is_scoped = metric_scope(metric) is not ConditionScope.FACTION
    return Comparison(
        metric=metric,
        operator=ConditionOperator.GTE,
        value=0,
        subject_id=SUBJECT_PLACEHOLDER if is_scoped else None,
        threshold=_template_threshold(template, metric),
    )


def _template_threshold(
    template: EventDefinition, metric: ConditionMetric
) -> int | None:
    for tier in template.tiers:
        for comparison in iter_comparisons(tier.trigger):
            if comparison.metric is metric and comparison.threshold is not None:
                return comparison.threshold
    return None
