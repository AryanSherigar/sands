from app.engine.diplomacy.war_score import tally_war_scores
from app.engine.sieges.phase import SiegePhase

from tests.engine.sieges.builders import (
    BESIEGER,
    SCENARIO,
    TARGET_OWNER,
    TARGET_REGION,
    add_resolved_battle,
    make_siege_world,
    run_phase,
)

MAX_TURNS = 20


def _play_until_conquered(world):
    kinds: list[str] = []
    for _ in range(MAX_TURNS):
        result = run_phase(SiegePhase(), world)
        world = result.world
        kinds += [event.kind for event in result.events]
        tally_war_scores(world, SCENARIO)
        world.clock.turn += 1
        if world.regions[TARGET_REGION].owner_id == BESIEGER:
            break
    return world, kinds


def test_a_won_battle_leads_to_siege_occupation_score_and_transfer() -> None:
    world = make_siege_world()
    add_resolved_battle(world)

    world, kinds = _play_until_conquered(world)

    region = world.regions[TARGET_REGION]
    assert region.owner_id == BESIEGER
    assert region.occupation is None
    assert TARGET_OWNER in region.claimant_ids
    assert kinds[0] == "siege_started"
    assert kinds.index("region_occupied") < kinds.index("region_conquered")
    assert kinds[-1] == "region_conquered"
    assert world.sieges == []
    assert world.wars[0].occupation_points_attacker == 20
    assert [item.faction_id for item in world.coalition.conquests] == [BESIEGER]


def test_the_siege_takes_several_turns_not_one() -> None:
    world = make_siege_world()
    add_resolved_battle(world)

    first = run_phase(SiegePhase(), world)

    assert first.world.sieges[0].progress < SCENARIO.tuning.siege.full_progress
    assert first.world.regions[TARGET_REGION].occupation is None
