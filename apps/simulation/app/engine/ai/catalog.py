from collections.abc import Callable

from app.engine.ai.candidates import Candidate
from app.engine.ai.generators.diplomacy import (
    demand_candidates,
    forgery_candidates,
    talks_candidates,
    war_candidates,
)
from app.engine.ai.generators.economy import tax_rate_candidates
from app.engine.ai.generators.feint import feint_candidates
from app.engine.ai.generators.levy import levy_candidates
from app.engine.ai.generators.movement import movement_candidates
from app.engine.ai.generators.order import uprising_candidates
from app.engine.ai.generators.recon import scout_candidates
from app.engine.ai.generators.treasury import (
    disband_candidates,
    loan_candidates,
    pay_candidates,
)
from app.engine.commands.check import check_command
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario

CandidateGenerator = Callable[
    [WorldState, StrategyScenario, FactionId], list[Candidate]
]

GENERATORS: tuple[CandidateGenerator, ...] = (
    tax_rate_candidates,
    loan_candidates,
    pay_candidates,
    disband_candidates,
    levy_candidates,
    uprising_candidates,
    movement_candidates,
    scout_candidates,
    feint_candidates,
    war_candidates,
    demand_candidates,
    talks_candidates,
    forgery_candidates,
)


def generate_candidates(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for generator in GENERATORS:
        candidates.extend(generator(world, scenario, faction_id))
    return candidates


def legal_candidates(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    candidates: list[Candidate],
) -> list[Candidate]:
    return [
        candidate
        for candidate in candidates
        if check_command(
            world,
            scenario,
            candidate.order,
            faction_id=faction_id,
            expected_turn=world.clock.turn,
            expected_wave=0,
        ).flag
        is None
    ]
