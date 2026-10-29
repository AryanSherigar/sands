from uuid import UUID

import pytest
from app.engine.hashing import world_hash
from app.engine.world_document import world_from_document
from app.engine.world_init import new_world
from app.exceptions.world_exceptions import UnknownPlayerFactionError
from app.models.world_player import PlayerRuler
from app.models.world_state import CURRENT_AI_RULESET, CURRENT_SUCCESSION_RULESET
from strategy_contracts.examples import load_three_crowns_expanded

PLAYTHROUGH_ID = UUID("11111111-1111-1111-1111-111111111111")
SEED = 20261026
PLAYER_FACTION = "house_ashford"


def _ruler() -> PlayerRuler:
    return PlayerRuler(
        name="Valdren",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
    )


def _world(seed: int = SEED, faction: str = PLAYER_FACTION):
    return new_world(
        load_three_crowns_expanded(), PLAYTHROUGH_ID, seed, faction, _ruler()
    )


def test_every_map_region_faction_and_army_is_created() -> None:
    world = _world()
    assert len(world.regions) == 10
    assert len(world.factions) == 3
    assert len(world.armies) == 5
    assert world.clock.turn == 0
    assert world.rng.seed == SEED
    assert world.internal_ruleset == 2
    assert world.logistics_ruleset == 1
    assert world.summary_ruleset == 2
    assert world.diplomacy_ruleset == 1
    assert world.ai_ruleset == CURRENT_AI_RULESET == 2
    assert world.aims == {}


def test_only_the_chosen_faction_is_the_player() -> None:
    world = _world()
    players = [fid for fid, faction in world.factions.items() if faction.is_player]
    assert players == [PLAYER_FACTION]


def test_claims_and_commanders_are_linked() -> None:
    world = _world()
    assert "house_dunwick" in world.regions["brennmoor"].claimant_ids
    linked = [c for c in world.commanders.values() if c.army_id is not None]
    assert linked
    for commander in linked:
        assert world.armies[commander.army_id].commander_id == commander.id


def test_relations_are_stored_sorted() -> None:
    for relation in _world().relations:
        assert relation.faction_a < relation.faction_b


def test_same_inputs_give_the_same_hash_and_a_new_seed_changes_it() -> None:
    assert world_hash(_world()) == world_hash(_world())
    assert world_hash(_world()) != world_hash(_world(seed=SEED + 1))


def test_world_survives_a_document_round_trip() -> None:
    world = _world()
    assert world_from_document(world.model_dump(mode="json")) == world


def test_unknown_player_faction_is_rejected() -> None:
    with pytest.raises(UnknownPlayerFactionError):
        _world(faction="house_nobody")


def test_scenario_claims_become_grounds_against_the_current_owner() -> None:
    world = _world()

    claims = {
        (ground.holder_faction_id, ground.target_faction_id, ground.region_id)
        for ground in world.grounds
    }
    assert claims == {("house_dunwick", "house_ashford", "brennmoor")}
    ground = world.grounds[0]
    assert ground.strength == 100
    assert ground.holder_leader_id == "harl"


def test_new_world_enables_pressure_ruleset() -> None:
    assert _world().pressure_ruleset == 1


def test_new_world_enables_peace_ruleset() -> None:
    assert _world().peace_ruleset == 1


def test_new_world_enables_alliance_ruleset() -> None:
    assert _world().alliance_ruleset == 1


def test_new_worlds_use_the_current_succession_ruleset_with_no_crises() -> None:
    world = _world()

    assert world.succession_ruleset == CURRENT_SUCCESSION_RULESET
    assert world.succession.crises == []
