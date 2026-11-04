from app.engine.ai.generators.diplomacy import (
    demand_candidates,
    forgery_candidates,
    peace_candidates,
    talks_candidates,
    war_candidates,
)
from app.engine.promises.signing import sign_sworn_promise
from app.models.orders import (
    CallNegotiationOrder,
    DeclareWarOrder,
    DiplomaticPlayOrder,
    FabricateClaimOrder,
    SuePeaceOrder,
)
from app.models.world_ai import AimState
from app.models.world_diplomacy import (
    DiplomaticPlayState,
    GroundState,
    RelationState,
    TruceState,
    WarState,
)
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.stances import ScoreCategory
from strategy_contracts.terms import (
    CedeRegionTerm,
    PayGoldTerm,
    PromiseKind,
    SwornPromiseTerm,
)

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)

TUNING = SCENARIO.tuning.ai
STRENGTH = 80


def _world(traits: list[str] | None = None):
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, traits or [])
    return world


def _ground(world, target: str, region: str = "fenwatch", strength: int = STRENGTH):
    world.grounds.append(
        GroundState(
            id=f"ground_{len(world.grounds) + 1}",
            kind=GroundKind.CLAIM,
            holder_faction_id=CAUTIOUS_RIVAL,
            holder_leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
            target_faction_id=target,
            region_id=region,
            strength=strength,
            since_turn=0,
            is_personal=False,
        )
    )


def _war(world, first: str, second: str) -> None:
    low, high = sorted((first, second))
    world.relations = [
        RelationState(
            faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=0
        )
    ]
    world.wars.append(
        WarState(id="war_x", attacker_id=first, defender_id=second, started_turn=0)
    )


def _wars(world):
    return war_candidates(world, SCENARIO, CAUTIOUS_RIVAL)


def test_a_usable_ground_offers_a_war_declaration() -> None:
    world = _world()
    _ground(world, WRATHFUL_RIVAL)

    candidates = _wars(world)

    assert len(candidates) == 1
    order = candidates[0].order
    assert isinstance(order, DeclareWarOrder)
    assert (order.target_faction_id, order.ground_id) == (WRATHFUL_RIVAL, "ground_1")
    assert candidates[0].category == ScoreCategory.ATTACK
    assert (
        candidates[0].base_score
        == TUNING.war_base_bonus + STRENGTH // TUNING.ground_strength_divisor + 8
    )


def test_no_ground_means_no_war_declaration() -> None:
    assert _wars(_world()) == []


def test_unusable_ground_is_not_used() -> None:
    world = _world()
    _ground(world, WRATHFUL_RIVAL, strength=0)

    assert _wars(world) == []


def test_war_against_the_player_can_be_declared() -> None:
    world = _world()
    _ground(world, PLAYER, region="ashford")

    assert [c.order.target_faction_id for c in _wars(world)] == [PLAYER]


def test_bound_or_already_hostile_targets_are_skipped() -> None:
    truce = _world()
    _ground(truce, WRATHFUL_RIVAL)
    truce.truces.append(
        TruceState(faction_a=CAUTIOUS_RIVAL, faction_b=WRATHFUL_RIVAL, expires_turn=9)
    )
    at_war = _world()
    _ground(at_war, WRATHFUL_RIVAL)
    _war(at_war, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    assert _wars(truce) == []
    assert _wars(at_war) == []


def test_a_weaker_ruler_scores_war_lower() -> None:
    strong = _world()
    _ground(strong, WRATHFUL_RIVAL)
    weak = _world()
    _ground(weak, WRATHFUL_RIVAL)
    for army in weak.armies.values():
        if army.owner_id == CAUTIOUS_RIVAL:
            army.troops = {TroopType.INFANTRY: 5}

    assert _wars(weak)[0].base_score < _wars(strong)[0].base_score


def test_a_second_front_costs_points() -> None:
    quiet = _world()
    _ground(quiet, WRATHFUL_RIVAL)
    busy = _world()
    _ground(busy, WRATHFUL_RIVAL)
    _war(busy, CAUTIOUS_RIVAL, PLAYER)

    drop = _wars(quiet)[0].base_score - _wars(busy)[0].base_score

    assert drop == TUNING.second_front_penalty


def _demands(world):
    return demand_candidates(world, SCENARIO, CAUTIOUS_RIVAL)


def test_a_stronger_ruler_demands_gold_from_a_weaker_ai_neighbour() -> None:
    candidates = _demands(_world())

    assert len(candidates) == 1
    order = candidates[0].order
    assert isinstance(order, DiplomaticPlayOrder)
    assert order.target_faction_id == WRATHFUL_RIVAL
    assert order.demands == [
        PayGoldTerm(
            payer_id=WRATHFUL_RIVAL, payee_id=CAUTIOUS_RIVAL, amount=TUNING.demand_gold
        )
    ]
    assert candidates[0].category == ScoreCategory.HOARD


def test_demands_never_target_the_player() -> None:
    world = _world()
    world.armies["army_ashford_1"].troops = {TroopType.INFANTRY: 1}
    world.armies["army_ashford_2"].troops = {TroopType.INFANTRY: 1}

    assert PLAYER not in {c.order.target_faction_id for c in _demands(world)}


def test_no_demand_without_enough_strength() -> None:
    world = _world()
    for army in world.armies.values():
        if army.owner_id == CAUTIOUS_RIVAL:
            army.troops = {TroopType.INFANTRY: 20}

    assert _demands(world) == []


def test_a_claim_turns_into_a_demand_for_the_region() -> None:
    world = _world()
    _ground(world, WRATHFUL_RIVAL)

    terms = [c.order.demands[0] for c in _demands(world)]

    assert (
        CedeRegionTerm(
            from_faction_id=WRATHFUL_RIVAL,
            to_faction_id=CAUTIOUS_RIVAL,
            region_id="fenwatch",
        )
        in terms
    )


def test_an_open_play_suppresses_new_demands() -> None:
    world = _world()
    world.plays.append(
        DiplomaticPlayState(
            id="play_1",
            attacker_id=CAUTIOUS_RIVAL,
            defender_id=WRATHFUL_RIVAL,
            stage="demand",
            due_turn=3,
        )
    )

    assert _demands(world) == []


def test_talks_go_to_non_hostile_ai_factions_only() -> None:
    candidates = talks_candidates(_world(), SCENARIO, CAUTIOUS_RIVAL)

    assert [c.order.target_faction_id for c in candidates] == [WRATHFUL_RIVAL]
    assert isinstance(candidates[0].order, CallNegotiationOrder)
    assert candidates[0].category == ScoreCategory.ALLY


def test_no_talks_with_an_enemy() -> None:
    world = _world()
    _war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    assert talks_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []


def _attack_aim(world) -> None:
    world.aims[CAUTIOUS_RIVAL] = AimState(
        category=ScoreCategory.ATTACK,
        target_faction_id=WRATHFUL_RIVAL,
        chosen_turn=0,
        leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
        capital_held=True,
    )


def _forgeries(world):
    return forgery_candidates(world, SCENARIO, CAUTIOUS_RIVAL)


def test_a_cunning_ruler_forges_a_claim_on_a_border_region() -> None:
    world = _world(["treacherous"])
    _attack_aim(world)

    candidates = _forgeries(world)

    assert len(candidates) == 1
    assert candidates[0].order == FabricateClaimOrder(
        faction_id=CAUTIOUS_RIVAL,
        target_faction_id=WRATHFUL_RIVAL,
        region_id="fenwatch",
    )
    assert candidates[0].category == ScoreCategory.ATTACK
    assert candidates[0].base_score >= TUNING.forgery_bonus


def test_an_honest_ruler_never_forges() -> None:
    world = _world(["honorable"])
    _attack_aim(world)

    assert _forgeries(world) == []


def test_no_forgery_when_a_usable_ground_exists_or_without_an_aim() -> None:
    with_ground = _world(["treacherous"])
    _attack_aim(with_ground)
    _ground(with_ground, WRATHFUL_RIVAL)

    assert _forgeries(with_ground) == []
    assert _forgeries(_world(["treacherous"])) == []


def _weary_scenario():
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.overtures.peace_offer_min_strain = 0
    return scenario


def test_a_war_weary_faction_offers_peace_in_its_war() -> None:
    world = _world()
    _war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    candidates = peace_candidates(world, _weary_scenario(), CAUTIOUS_RIVAL)

    assert [c.order for c in candidates] == [
        SuePeaceOrder(faction_id=CAUTIOUS_RIVAL, war_id="war_x")
    ]
    assert candidates[0].category == ScoreCategory.ALLY
    assert candidates[0].base_score == TUNING.peace_bonus


def test_a_faction_that_is_not_weary_offers_no_peace() -> None:
    world = _world()
    _war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.overtures.peace_offer_min_strain = 1000
    scenario.tuning.overtures.peace_offer_max_will = 0

    assert peace_candidates(world, scenario, CAUTIOUS_RIVAL) == []


def test_peace_is_not_offered_when_the_toggle_is_off() -> None:
    world = _world()
    _war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)
    scenario = _weary_scenario()
    scenario.toggles.is_ai_peace_enabled = False

    assert peace_candidates(world, scenario, CAUTIOUS_RIVAL) == []


def test_peace_is_not_offered_to_the_player() -> None:
    world = _world()
    _war(world, CAUTIOUS_RIVAL, PLAYER)

    assert peace_candidates(world, _weary_scenario(), CAUTIOUS_RIVAL) == []


def _sworn_world(traits: list[str]):
    world = _world(traits)
    _ground(world, WRATHFUL_RIVAL)
    sign_sworn_promise(
        world,
        SwornPromiseTerm(
            promisor_id=CAUTIOUS_RIVAL,
            beneficiary_id=WRATHFUL_RIVAL,
            promise=PromiseKind.NEVER_ATTACK_FACTION,
            duration_turns=5,
        ),
        None,
    )
    return world


def test_war_candidate_skipped_for_an_honorable_oath_holder() -> None:
    assert _wars(_sworn_world(["honorable"])) == []


def _with_ground(traits: list[str]):
    world = _world(traits)
    _ground(world, WRATHFUL_RIVAL)
    return world


def test_war_candidate_score_lowered_for_a_dishonorable_oath_holder() -> None:
    baseline = _wars(_with_ground(["treacherous"]))[0].base_score

    sworn = _wars(_sworn_world(["treacherous"]))

    assert len(sworn) == 1
    assert sworn[0].base_score == baseline - TUNING.oath_break_penalty


def test_a_hoarding_target_is_a_juicier_war_target() -> None:
    plain = _world()
    _ground(plain, WRATHFUL_RIVAL)
    rich = _world()
    _ground(rich, WRATHFUL_RIVAL)
    for faction_id, faction in rich.factions.items():
        faction.treasury = 5000 if faction_id == WRATHFUL_RIVAL else 0

    assert _wars(rich)[0].base_score > _wars(plain)[0].base_score
