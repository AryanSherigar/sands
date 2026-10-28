from app.engine.diplomacy.counters import next_counter
from app.models.world_diplomacy import CommitmentState
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.scenario import RelationSetup, StrategyScenario
from strategy_contracts.terms import VassalTerm


def _term_for(setup: RelationSetup) -> VassalTerm:
    block = setup.vassalage
    assert block is not None
    vassal_id = (
        setup.faction_b if block.overlord_id == setup.faction_a else setup.faction_a
    )
    return VassalTerm(
        overlord_id=block.overlord_id,
        vassal_id=vassal_id,
        tribute_share_percent=block.tribute_share_percent,
        levy_share_percent=block.levy_share_percent,
        is_foreign_policy_controlled=block.is_foreign_policy_controlled,
        has_garrison_rights=block.has_garrison_rights,
        duration_turns=block.duration_turns,
    )


def seed_starting_vassalages(world: WorldState, scenario: StrategyScenario) -> None:
    if world.vassal_ruleset < 1:
        return
    for setup in scenario.starting.relations:
        if setup.vassalage is None:
            continue
        term = _term_for(setup)
        end_turn = (
            world.clock.turn + term.duration_turns if term.duration_turns else None
        )
        world.commitments.append(
            CommitmentState(
                id=f"commitment_{next_counter(world, CounterKind.COMMITMENT)}",
                term=term,
                start_turn=world.clock.turn,
                end_turn=end_turn,
            )
        )
