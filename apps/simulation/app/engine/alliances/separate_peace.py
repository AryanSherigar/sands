from app.engine.alliances.refusal import break_alliance
from app.engine.alliances.registry import active_alliances, alliance_term
from app.engine.pressure.wars import side_of
from app.models.world_diplomacy import CommitmentState, WarState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario


def _binding_alliances(
    world: WorldState, war: WarState, party: FactionId, parties: list[FactionId]
) -> list[CommitmentState]:
    binding: list[CommitmentState] = []
    for alliance in active_alliances(world, party):
        term = alliance_term(alliance)
        partner = term.faction_b if term.faction_a == party else term.faction_a
        is_same_side = side_of(war, partner) is side_of(war, party)
        if term.is_separate_peace_banned and partner not in parties and is_same_side:
            binding.append(alliance)
    return binding


def breach_separate_peace(
    world: WorldState,
    scenario: StrategyScenario,
    war: WarState,
    parties: list[FactionId],
) -> list[EventLogEntry]:
    events: list[EventLogEntry] = []
    for party in parties:
        for alliance in _binding_alliances(world, war, party, parties):
            events += break_alliance(world, scenario, party, alliance)
    return events
