from app.engine.negotiation_memory import MAX_MEMORIES
from app.models.world_character import OpinionReason, OpinionState
from app.models.world_state import OPINION_CARRY_RULESET, WorldState
from strategy_contracts.ids import LeaderId
from strategy_contracts.scenario import StrategyScenario

PERCENT = 100
INHERITED_PREFIX = "inherited:"


def _carried(value: int, carry_percent: int) -> int:
    magnitude = abs(value) * carry_percent // PERCENT
    return magnitude if value >= 0 else -magnitude


def carry_opinions(
    world: WorldState,
    scenario: StrategyScenario,
    predecessor_id: LeaderId,
    successor_id: LeaderId,
) -> None:
    if world.succession_ruleset < OPINION_CARRY_RULESET:
        return
    _carry_regard_for_predecessor(world, scenario, predecessor_id, successor_id)
    _carry_own_regard(world, scenario, predecessor_id, successor_id)


def _scaled_reasons(
    reasons: list[OpinionReason], carry_percent: int
) -> list[OpinionReason]:
    return [
        OpinionReason(
            cause=f"{INHERITED_PREFIX}{reason.cause}",
            value=_carried(reason.value, carry_percent),
            fade_per_turn=reason.fade_per_turn,
        )
        for reason in reasons
        if _carried(reason.value, carry_percent) != 0
    ]


def _carry_own_regard(
    world: WorldState,
    scenario: StrategyScenario,
    predecessor_id: LeaderId,
    successor_id: LeaderId,
) -> None:
    predecessor = world.leaders.get(predecessor_id)
    successor = world.leaders.get(successor_id)
    if predecessor is None or successor is None:
        return
    carry_percent = scenario.tuning.succession.opinion_carry_percent
    for target_id, regard in sorted(predecessor.opinions.items()):
        if target_id == successor_id:
            continue
        inherited = successor.opinions.setdefault(
            target_id, OpinionState(target_id=target_id)
        )
        inherited.reasons += _scaled_reasons(regard.reasons, carry_percent)
    successor.memories += [
        memory.model_copy(
            update={
                "kind": f"{INHERITED_PREFIX}{memory.kind}",
                "weight": _carried(memory.weight, carry_percent),
            }
        )
        for memory in predecessor.memories
        if _carried(memory.weight, carry_percent) != 0
    ]
    del successor.memories[MAX_MEMORIES:]


def _carry_regard_for_predecessor(
    world: WorldState,
    scenario: StrategyScenario,
    predecessor_id: LeaderId,
    successor_id: LeaderId,
) -> None:
    carry_percent = scenario.tuning.succession.opinion_carry_percent
    for holder_id, holder in sorted(world.leaders.items()):
        regard = holder.opinions.get(predecessor_id)
        if regard is None or holder_id in (predecessor_id, successor_id):
            continue
        inherited = holder.opinions.setdefault(
            successor_id, OpinionState(target_id=successor_id)
        )
        inherited.reasons += _scaled_reasons(regard.reasons, carry_percent)
