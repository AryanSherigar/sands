from uuid import UUID

from app.engine.vassals.registry import overlord_of, vassal_term, vassalage_of
from app.engine.vassals.starting import seed_starting_vassalages
from app.engine.world_init import new_world
from app.models.world_player import PlayerRuler
from strategy_contracts.enums import RelationStatus
from strategy_contracts.examples import load_three_crowns_expanded
from strategy_contracts.vassal import VassalageSetup

PLAYTHROUGH_ID = UUID("33333333-3333-3333-3333-333333333333")
SEED = 7
OVERLORD = "house_ashford"
VASSAL = "house_carrow"
TRIBUTE = 35
LEVY = 15


def _scenario_with_vassalage():
    scenario = load_three_crowns_expanded()
    for setup in scenario.starting.relations:
        if {setup.faction_a, setup.faction_b} == {OVERLORD, VASSAL}:
            setup.status = RelationStatus.PEACE
            setup.vassalage = VassalageSetup(
                overlord_id=OVERLORD,
                tribute_share_percent=TRIBUTE,
                levy_share_percent=LEVY,
                is_foreign_policy_controlled=True,
            )
    return scenario


def _world(scenario):
    ruler = PlayerRuler(
        name="Valdren",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
    )
    return new_world(scenario, PLAYTHROUGH_ID, SEED, OVERLORD, ruler)


def test_starting_block_becomes_an_active_commitment() -> None:
    world = _world(_scenario_with_vassalage())

    commitment = vassalage_of(world, VASSAL)

    assert commitment is not None
    term = vassal_term(commitment)
    assert (term.tribute_share_percent, term.levy_share_percent) == (TRIBUTE, LEVY)
    assert term.is_foreign_policy_controlled
    assert overlord_of(world, VASSAL) == OVERLORD
    assert commitment.end_turn is None


def test_scenario_without_a_block_seeds_nothing() -> None:
    assert vassalage_of(_world(load_three_crowns_expanded()), VASSAL) is None


def test_legacy_ruleset_seeds_nothing() -> None:
    scenario = _scenario_with_vassalage()
    world = _world(load_three_crowns_expanded())
    world.vassal_ruleset = 0

    seed_starting_vassalages(world, scenario)

    assert vassalage_of(world, VASSAL) is None
