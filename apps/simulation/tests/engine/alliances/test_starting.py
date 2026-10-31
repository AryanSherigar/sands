from uuid import UUID

from app.engine.alliances.registry import alliance_between, alliance_term, allies_of
from app.engine.diplomacy.war_declaration import declare_war
from app.engine.world_init import new_world
from app.models.orders import DeclareWarOrder
from app.models.world_player import PlayerRuler
from strategy_contracts.alliance import AllianceType
from strategy_contracts.enums import RelationStatus
from strategy_contracts.examples import load_three_crowns_expanded

PLAYTHROUGH_ID = UUID("22222222-2222-2222-2222-222222222222")
SEED = 7
ALLY_A = "house_ashford"
ALLY_B = "house_carrow"


def _scenario_with_starting_alliance():
    scenario = load_three_crowns_expanded()
    for setup in scenario.starting.relations:
        if {setup.faction_a, setup.faction_b} == {ALLY_A, ALLY_B}:
            setup.status = RelationStatus.ALLIANCE
    return scenario


def _world(scenario):
    ruler = PlayerRuler(
        name="Valdren",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
    )
    return new_world(scenario, PLAYTHROUGH_ID, SEED, ALLY_A, ruler)


def test_starting_alliance_relation_becomes_a_forever_defensive_commitment() -> None:
    world = _world(_scenario_with_starting_alliance())

    commitment = alliance_between(world, ALLY_A, ALLY_B)

    assert commitment is not None
    term = alliance_term(commitment)
    assert term.alliance_type is AllianceType.DEFENSIVE
    assert term.duration_turns == 0
    assert term.is_separate_peace_banned is False
    assert commitment.end_turn is None
    assert allies_of(world, ALLY_A) == [ALLY_B]


def test_scenario_without_starting_alliances_has_no_alliance_commitments() -> None:
    world = _world(load_three_crowns_expanded())

    assert world.commitments == []


def test_starting_alliance_triggers_a_call_when_its_partner_is_attacked() -> None:
    world = _world(_scenario_with_starting_alliance())
    declare_war(
        world,
        load_three_crowns_expanded(),
        DeclareWarOrder(faction_id="house_dunwick", target_faction_id=ALLY_A),
    )

    assert [(call.caller_id, call.ally_id) for call in world.alliance.calls] == [
        (ALLY_A, ALLY_B)
    ]
