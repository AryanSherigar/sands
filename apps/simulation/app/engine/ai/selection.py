from app.engine.ai.candidates import ScoredCandidate
from app.engine.commands.budget import command_cost
from app.engine.commands.timing import command_slot
from app.engine.rng import DeterministicRng
from app.models.world_state import WorldState
from strategy_contracts.ai import AiTuning
from strategy_contracts.scenario import StrategyScenario

CommandSlot = tuple[str, str]


def select_orders(
    scored: list[ScoredCandidate],
    *,
    budget: int,
    tuning: AiTuning,
    world: WorldState,
    scenario: StrategyScenario,
    rng: DeterministicRng,
) -> list[ScoredCandidate]:
    remaining = [item for item in scored if item.score >= tuning.minimum_score]
    picked: list[ScoredCandidate] = []
    used_slots: set[CommandSlot] = set()
    while True:
        options = _affordable(remaining, budget, used_slots, world, scenario)
        if not options:
            return picked
        choice = _sample_near_best(options, tuning.variance_margin, rng)
        picked.append(choice)
        remaining.remove(choice)
        used_slots.add(command_slot(choice.candidate.order))
        budget -= command_cost(choice.candidate.order, scenario, world)


def _affordable(
    remaining: list[ScoredCandidate],
    budget: int,
    used_slots: set[CommandSlot],
    world: WorldState,
    scenario: StrategyScenario,
) -> list[ScoredCandidate]:
    options = [
        item
        for item in remaining
        if command_slot(item.candidate.order) not in used_slots
        and command_cost(item.candidate.order, scenario, world) <= budget
    ]
    return sorted(options, key=_ordering_key)


def _ordering_key(item: ScoredCandidate) -> tuple[int, CommandSlot, str]:
    order = item.candidate.order
    return (-item.score, command_slot(order), order.kind)


def _sample_near_best(
    options: list[ScoredCandidate], margin: int, rng: DeterministicRng
) -> ScoredCandidate:
    floor = options[0].score - margin
    near_best = [item for item in options if item.score >= floor]
    weights = [item.score - floor + 1 for item in near_best]
    return rng.weighted_choice(near_best, weights)
