from app.engine.diplomacy.grounds import grant_ground
from app.engine.diplomacy.phase import DiplomacyPhase
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import (
    CommitmentState,
    CommitmentStatus,
    TruceState,
    WarGoalState,
)
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus
from strategy_contracts.terms import NonAggressionTerm

from tests.engine.diplomacy.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_warning,
    make_world,
    queue_npc_order,
    run_phase,
)

ATTACKER = WRATHFUL_RIVAL
DEFENDER = PLAYER
TUNING = SCENARIO.tuning.diplomacy


def _claim(world):
    return grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=ATTACKER,
        target_faction_id=DEFENDER,
        region_id="brennmoor",
    )


def _declare(world, ground_id: str | None = None):
    order = DeclareWarOrder(
        faction_id=ATTACKER, target_faction_id=DEFENDER, ground_id=ground_id
    )
    return queue_npc_order(world, SCENARIO, order)


def _relation(world, first: str, second: str):
    pair = tuple(sorted((first, second)))
    return next(
        item for item in world.relations if (item.faction_a, item.faction_b) == pair
    )


def _warned_world_with_claim():
    world = make_world()
    ground = _claim(world)
    add_warning(world, ATTACKER, DEFENDER)
    return _declare(world, ground.id), ground


def test_usable_claim_creates_war_spends_ground_and_names_goal() -> None:
    world, ground = _warned_world_with_claim()
    before = world.factions[ATTACKER].reputation

    result = run_phase(DiplomacyPhase(), world)

    war = result.world.wars[0]
    assert (war.attacker_id, war.defender_id) == (ATTACKER, DEFENDER)
    assert war.ground_kind == GroundKind.CLAIM
    assert war.goals == [
        WarGoalState(faction_id=ATTACKER, kind=GroundKind.CLAIM, region_id="brennmoor")
    ]
    assert ground.id not in [item.id for item in result.world.grounds]
    assert result.world.factions[ATTACKER].reputation == before
    assert "war_declared" in [event.kind for event in result.events]


def test_war_sets_relation_to_war_and_clears_truce() -> None:
    world, _ = _warned_world_with_claim()
    world.truces.append(
        TruceState(faction_a=DEFENDER, faction_b=ATTACKER, expires_turn=10)
    )

    result = run_phase(DiplomacyPhase(), world)

    assert _relation(result.world, ATTACKER, DEFENDER).status == RelationStatus.WAR
    assert result.world.truces == []
    assert [mark.faction_id for mark in result.world.oathbreakers] == [ATTACKER]


def test_declaring_without_ground_costs_reputation_and_stability() -> None:
    world = _declare(make_world())
    before = world.factions[ATTACKER]

    result = run_phase(DiplomacyPhase(), world)

    after = result.world.factions[ATTACKER]
    assert after.reputation == before.reputation - TUNING.no_ground_reputation_cost
    assert after.stability == before.stability - TUNING.no_ground_stability_cost
    assert result.world.wars[0].goals == []


def test_declaring_during_a_pact_marks_oathbreaker_and_breaches_it() -> None:
    world, _ = _warned_world_with_claim()
    pact = NonAggressionTerm(faction_a=DEFENDER, faction_b=ATTACKER, duration_turns=5)
    world.commitments.append(
        CommitmentState(id="commitment_1", term=pact, start_turn=0)
    )
    before = world.factions[ATTACKER]

    result = run_phase(DiplomacyPhase(), world)

    after = result.world.factions[ATTACKER]
    assert result.world.commitments[0].status == CommitmentStatus.BREACHED
    assert [mark.faction_id for mark in result.world.oathbreakers] == [ATTACKER]
    assert after.reputation == before.reputation - TUNING.breach_reputation_cost
    assert after.stability == before.stability - TUNING.breach_stability_cost


def test_unwarned_declaration_with_ground_is_surprise_with_small_cost() -> None:
    world = make_world()
    ground = _claim(world)
    world = _declare(world, ground.id)
    before = world.factions[ATTACKER]

    result = run_phase(DiplomacyPhase(), world)

    after = result.world.factions[ATTACKER]
    assert result.world.wars[0].is_surprise is True
    assert after.reputation == before.reputation - TUNING.surprise_reputation_cost
    assert after.stability == before.stability


def test_mutual_declarations_make_one_war_and_refund_the_second() -> None:
    world = _declare(make_world())
    crossing = DeclareWarOrder(faction_id=DEFENDER, target_faction_id=ATTACKER)
    world = queue_npc_order(world, SCENARIO, crossing)
    assert world.factions[DEFENDER].orders_remaining == 4

    result = run_phase(DiplomacyPhase(), world)

    assert len(result.world.wars) == 1
    first, second = sorted([ATTACKER, DEFENDER])
    assert result.world.wars[0].attacker_id == first
    assert result.world.factions[second].orders_remaining == 6
