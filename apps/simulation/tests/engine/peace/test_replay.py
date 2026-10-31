from app.engine.ai.headless import run_headless
from app.engine.hashing import canonical_world_json, world_hash
from app.engine.peace.hostages import hold_hostage
from app.engine.peace.signing import sign_peace
from app.engine.peace.succession import leader_died
from app.models.world_peace import BreachPressureState
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns_expanded
from strategy_contracts.terms import HostageTerm

from tests.engine.peace.builders import (
    PLAYER,
    WRATHFUL_RIVAL,
    add_war,
    make_peace_card,
    make_world,
    set_score,
)
from tests.engine.peace.builders import (
    SCENARIO as FIXTURE_SCENARIO,
)

SCENARIO = load_three_crowns_expanded()
RULER = PlayerRuler(
    name="Valdren", trait_ids=["honorable", "cautious"], ambition_ids=["ambition_peace"]
)
TURNS = 12
SEEDS = (3, 11)
MAX_PRESSURE = 100


def _signed_world() -> WorldState:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    term = HostageTerm(
        giver_id=WRATHFUL_RIVAL,
        holder_id=PLAYER,
        leader_id=world.factions[WRATHFUL_RIVAL].leader_id,
        duration_turns=5,
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [term], tier="medium")
    sign_peace(world, FIXTURE_SCENARIO, card, "scene-1")
    return world


def test_signing_the_same_peace_twice_gives_identical_hashes() -> None:
    assert world_hash(_signed_world()) == world_hash(_signed_world())


def test_headless_games_replay_to_identical_hashes_and_peace_state() -> None:
    for seed in SEEDS:
        first = run_headless(SCENARIO, seed, TURNS, RULER)
        second = run_headless(SCENARIO, seed, TURNS, RULER)

        assert first.final_hash == second.final_hash
        assert first.final_world.peace == second.final_world.peace
        assert first.final_world.truces == second.final_world.truces


def test_pressure_stays_bounded_over_a_long_ai_game() -> None:
    world = run_headless(SCENARIO, SEEDS[0], TURNS, RULER).final_world
    assert world is not None

    assert all(0 <= e.pressure <= MAX_PRESSURE for e in world.peace.breach)


def test_peace_state_survives_a_document_round_trip() -> None:
    world = _signed_world()
    world.peace.breach.append(
        BreachPressureState(faction_a="aa", faction_b="bb", pressure=40)
    )
    leader_died(world, FIXTURE_SCENARIO, world.factions[PLAYER].leader_id)

    restored = WorldState.model_validate(world.model_dump(mode="json"))

    assert world_hash(restored) == world_hash(world)
    assert restored.peace == world.peace
    assert restored.truces == world.truces


def test_legacy_ruleset_world_hash_ignores_peace_fields() -> None:
    legacy = make_world()
    legacy.peace_ruleset = 0
    other = legacy.model_copy(deep=True)
    other.peace.breach.append(
        BreachPressureState(faction_a="aa", faction_b="bb", pressure=1)
    )

    text = canonical_world_json(legacy)
    assert '"peace":' not in text
    assert "peace_ruleset" not in text
    assert world_hash(legacy) == world_hash(other)


def test_hostage_release_is_part_of_the_hash() -> None:
    world = _signed_world()
    before = world_hash(world)
    hold_hostage(
        world,
        HostageTerm(
            giver_id=WRATHFUL_RIVAL,
            holder_id=PLAYER,
            leader_id=world.factions[WRATHFUL_RIVAL].leader_id,
            duration_turns=3,
        ),
        world.truces[0].id,
    )

    assert world_hash(world) != before
