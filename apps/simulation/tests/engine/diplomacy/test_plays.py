from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.diplomacy.plays import demand_limit_percent
from app.models.orders import CallNegotiationOrder, DiplomaticPlayOrder
from app.models.world_character import MemoryState
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.terms import CedeRegionTerm, PayGoldTerm

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    queue_npc_order,
    run_phase,
    set_traits,
)

ATTACKER = WRATHFUL_RIVAL
DEFENDER = CAUTIOUS_RIVAL


def _cede(region: str = "elmstead") -> DiplomaticPlayOrder:
    term = CedeRegionTerm(
        from_faction_id=DEFENDER, to_faction_id=ATTACKER, region_id=region
    )
    return DiplomaticPlayOrder(
        faction_id=ATTACKER, target_faction_id=DEFENDER, demands=[term]
    )


def _opened(world: WorldState, order) -> WorldState:
    return run_phase(DiplomacyPhase(), queue_npc_order(world, SCENARIO, order)).world


def _next_turn(world: WorldState):
    world.clock.turn += 1
    return run_phase(DiplomacyPhase(), world)


def test_demand_opens_play_due_next_turn() -> None:
    world = _opened(make_world(), _cede())

    play = world.plays[0]
    assert (play.attacker_id, play.defender_id) == (ATTACKER, DEFENDER)
    assert (play.kind, play.stage, play.due_turn) == ("demand", "demand", 1)


def test_small_demand_to_cautious_weak_ruler_is_conceded() -> None:
    result = _next_turn(_opened(make_world(), _cede()))

    world = result.world
    assert world.regions["elmstead"].owner_id == ATTACKER
    assert world.plays[0].stage == "resolved"
    assert "play_conceded" in [event.kind for event in result.events]


def test_cession_grants_previous_owner_a_claim() -> None:
    world = _next_turn(_opened(make_world(), _cede())).world

    claims = [
        (g.holder_faction_id, g.target_faction_id, g.region_id) for g in world.grounds
    ]
    assert (DEFENDER, ATTACKER, "elmstead") in claims
    assert DEFENDER in world.regions["elmstead"].claimant_ids


def test_pay_gold_moves_treasury() -> None:
    term = PayGoldTerm(payer_id=DEFENDER, payee_id=ATTACKER, amount=10)
    order = DiplomaticPlayOrder(
        faction_id=ATTACKER, target_faction_id=DEFENDER, demands=[term]
    )
    world = _opened(make_world(), order)
    before = (world.factions[ATTACKER].treasury, world.factions[DEFENDER].treasury)

    world = _next_turn(world).world

    assert world.factions[ATTACKER].treasury == before[0] + 10
    assert world.factions[DEFENDER].treasury == before[1] - 10


def test_demand_to_proud_ruler_is_refused_and_starts_war_without_penalty() -> None:
    world = make_world()
    set_traits(world, DEFENDER, ["proud"])
    world = _opened(world, _cede())
    reputation = world.factions[ATTACKER].reputation

    result = _next_turn(world)

    war = result.world.wars[0]
    assert war.ground_kind == GroundKind.REFUSED_DEMAND
    assert result.world.regions["elmstead"].owner_id == DEFENDER
    assert result.world.factions[ATTACKER].reputation == reputation
    assert "play_refused" in [event.kind for event in result.events]


def test_leverage_raises_the_limit() -> None:
    world = make_world()
    set_traits(world, DEFENDER, [])
    world = _opened(world, _cede())
    weak = demand_limit_percent(world, SCENARIO, world.plays[0])
    for army in world.armies.values():
        if army.owner_id == ATTACKER:
            army.troops = {kind: count * 2 for kind, count in army.troops.items()}

    assert (weak, demand_limit_percent(world, SCENARIO, world.plays[0])) == (13, 26)


def test_talks_accepted_add_warm_memory() -> None:
    call = CallNegotiationOrder(faction_id=ATTACKER, target_faction_id=DEFENDER)
    world = _next_turn(_opened(make_world(), call)).world

    leader = world.leaders[world.factions[DEFENDER].leader_id]
    assert [memory.kind for memory in leader.memories] == ["talks_held"]


def test_talks_refused_when_the_ruler_holds_a_grudge() -> None:
    world = make_world()
    leader = world.leaders[world.factions[DEFENDER].leader_id]
    attacker_leader = world.factions[ATTACKER].leader_id
    leader.memories.append(
        MemoryState(kind="insult", turn=0, subject_id=attacker_leader, weight=-30)
    )
    call = CallNegotiationOrder(faction_id=ATTACKER, target_faction_id=DEFENDER)

    world = _next_turn(_opened(world, call)).world

    leader = world.leaders[world.factions[DEFENDER].leader_id]
    assert "talks_refused" in [memory.kind for memory in leader.memories]
