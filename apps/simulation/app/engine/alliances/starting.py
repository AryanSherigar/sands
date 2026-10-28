from app.engine.diplomacy.counters import next_counter
from app.models.world_diplomacy import CommitmentState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.terms import AllianceTerm


def seed_starting_alliances(world: WorldState, scenario: StrategyScenario) -> None:
    """A creator-authored alliance relation becomes a forever, defensive treaty."""
    if world.alliance_ruleset < 1:
        return
    pairs = sorted(
        {
            (min(item.faction_a, item.faction_b), max(item.faction_a, item.faction_b))
            for item in scenario.starting.relations
            if item.status == RelationStatus.ALLIANCE
        }
    )
    for faction_a, faction_b in pairs:
        world.commitments.append(
            CommitmentState(
                id=f"commitment_{next_counter(world, CounterKind.COMMITMENT)}",
                term=AllianceTerm(faction_a=faction_a, faction_b=faction_b),
                start_turn=world.clock.turn,
            )
        )
