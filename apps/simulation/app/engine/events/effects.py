from collections.abc import Callable
from dataclasses import dataclass

from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.overtures.succession_hook import remove_ruler_change
from app.engine.subjects import Subject, related_entity_id
from app.exceptions.condition_exceptions import UnsupportedEffectError
from app.models.base import WorldModel
from app.models.world_events import StateChange
from app.models.world_state import WorldState
from strategy_contracts.conditions import SUBJECT_PLACEHOLDER, ConditionScope
from strategy_contracts.events import EffectKind, EffectSpec
from strategy_contracts.scenario import StrategyScenario

MIN_SIGNED = -PERCENT
FLOOR = 0
CEILING = 10**9


@dataclass(frozen=True)
class EffectContext:
    world: WorldState
    faction_id: str
    subject: Subject
    scenario: StrategyScenario


Handler = Callable[[EffectContext, EffectSpec], list[StateChange]]


def apply_effect(context: EffectContext, effect: EffectSpec) -> list[StateChange]:
    handler = _HANDLERS.get(effect.kind)
    if handler is None:
        raise UnsupportedEffectError(f"effect {effect.kind.value} has no handler")
    return handler(context, effect)


def _shift(
    owner: WorldModel, attribute: str, delta: int, low: int, high: int, path: str
) -> list[StateChange]:
    before = getattr(owner, attribute)
    after = clamp(before + delta, low, high)
    if after == before:
        return []
    setattr(owner, attribute, after)
    return [StateChange(path=path, before=before, after=after)]


def _target_id(
    context: EffectContext, effect: EffectSpec, scope: ConditionScope
) -> str | None:
    if effect.target_id not in (None, SUBJECT_PLACEHOLDER):
        return effect.target_id
    return related_entity_id(context.world, context.subject, scope)


def _faction_stat(attribute: str, low: int, high: int) -> Handler:
    def apply(context: EffectContext, effect: EffectSpec) -> list[StateChange]:
        faction_id = effect.target_id or context.faction_id
        faction = context.world.factions.get(faction_id)
        if faction is None:
            return []
        path = f"factions.{faction_id}.{attribute}"
        return _shift(faction, attribute, effect.amount, low, high, path)

    return apply


def _entity_stat(
    scope: ConditionScope, table: str, attribute: str, low: int, high: int
) -> Handler:
    def apply(context: EffectContext, effect: EffectSpec) -> list[StateChange]:
        entity_id = _target_id(context, effect, scope)
        entity = getattr(context.world, table).get(entity_id)
        if entity is None:
            return []
        path = f"{table}.{entity_id}.{attribute}"
        return _shift(entity, attribute, effect.amount, low, high, path)

    return apply


def _all_unrest(context: EffectContext, effect: EffectSpec) -> list[StateChange]:
    changes: list[StateChange] = []
    for region_id in sorted(context.world.regions):
        region = context.world.regions[region_id]
        if region.owner_id == context.faction_id:
            path = f"regions.{region_id}.unrest"
            changes += _shift(region, "unrest", effect.amount, FLOOR, PERCENT, path)
    return changes


def _ruler_dies(context: EffectContext, effect: EffectSpec) -> list[StateChange]:
    faction_id = effect.target_id or context.faction_id
    return remove_ruler_change(context.world, context.scenario, faction_id)


_HANDLERS: dict[EffectKind, Handler] = {
    EffectKind.RULER_DIES: _ruler_dies,
    EffectKind.GOLD: _faction_stat("treasury", FLOOR, CEILING),
    EffectKind.STABILITY: _faction_stat("stability", FLOOR, PERCENT),
    EffectKind.REPUTATION: _faction_stat("reputation", MIN_SIGNED, PERCENT),
    EffectKind.UNREST: _all_unrest,
    EffectKind.REGION_UNREST: _entity_stat(
        ConditionScope.REGION, "regions", "unrest", FLOOR, PERCENT
    ),
    EffectKind.MANPOWER: _entity_stat(
        ConditionScope.REGION, "regions", "manpower", FLOOR, 10**9
    ),
    EffectKind.GOVERNOR_OPINION: _entity_stat(
        ConditionScope.GOVERNOR, "governors", "opinion_of_ruler", MIN_SIGNED, PERCENT
    ),
    EffectKind.ARMY_MORALE: _entity_stat(
        ConditionScope.ARMY, "armies", "morale", FLOOR, PERCENT
    ),
}
