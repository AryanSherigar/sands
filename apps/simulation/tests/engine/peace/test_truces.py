from app.engine.diplomacy.phase import DiplomacyPhase, TimePhase
from app.engine.peace.truces import (
    apply_breach_consequences,
    breach_agreements,
    expire_truces,
    grant_broken_promise_ground,
    truce_between,
)
from app.models.orders import DeclareWarOrder
from app.models.world_diplomacy import TruceState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.peace import PeaceTier

from tests.engine.diplomacy.builders import (
    add_warning,
    queue_npc_order,
    run_phase,
)
from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

TUNING = SCENARIO.tuning.diplomacy


def _truce(
    truce_id: str,
    expires_turn: int,
    tier: PeaceTier | None = PeaceTier.SHORT,
    guarantors: list[str] | None = None,
) -> TruceState:
    first, second = sorted((PLAYER, WRATHFUL_RIVAL))
    return TruceState(
        id=truce_id,
        faction_a=first,
        faction_b=second,
        expires_turn=expires_turn,
        tier=tier,
        guarantor_ids=guarantors or [],
    )


def test_expire_removes_only_elapsed_truces() -> None:
    world = make_world()
    world.clock.turn = 10
    world.truces = [_truce("truce_1", 9), _truce("truce_2", 10), _truce("truce_3", 11)]

    removed = expire_truces(world)

    assert [item.id for item in removed] == ["truce_1"]
    assert [item.id for item in world.truces] == ["truce_2", "truce_3"]


def test_perpetual_never_expires() -> None:
    world = make_world()
    world.clock.turn = 500
    world.truces = [_truce("truce_1", 0, PeaceTier.PERPETUAL)]

    assert expire_truces(world) == []
    assert len(world.truces) == 1


def test_time_phase_reports_expired_truces() -> None:
    world = make_world()
    world.clock.turn = 10
    world.truces = [_truce("truce_1", 9)]

    result = run_phase(TimePhase(), world)

    assert "truce_expired" in [event.kind for event in result.events]
    assert result.world.truces == []


def test_truce_between_matches_either_order() -> None:
    world = make_world()
    world.truces = [_truce("truce_1", 9)]

    assert truce_between(world, WRATHFUL_RIVAL, PLAYER) is world.truces[0]
    assert truce_between(world, PLAYER, CAUTIOUS_RIVAL) is None


def test_breach_costs_once_for_multiple_truces() -> None:
    world = make_world()
    world.truces = [_truce("truce_1", 99), _truce("truce_2", 99)]
    before = world.factions[WRATHFUL_RIVAL].model_copy(deep=True)

    breach_agreements(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)

    after = world.factions[WRATHFUL_RIVAL]
    assert after.reputation == before.reputation - TUNING.breach_reputation_cost
    assert after.stability == before.stability - TUNING.breach_stability_cost
    assert world.truces == []


def test_breach_adds_a_single_oathbreaker_mark() -> None:
    world = make_world()
    world.truces = [_truce("truce_1", 99)]
    breach_agreements(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)
    world.truces = [_truce("truce_2", 99)]

    breach_agreements(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)

    assert [mark.faction_id for mark in world.oathbreakers] == [WRATHFUL_RIVAL]


def test_breach_gives_guarantor_a_ground_without_a_war() -> None:
    world = make_world()
    world.truces = [_truce("truce_1", 99, guarantors=[CAUTIOUS_RIVAL])]

    breach_agreements(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)

    ground = world.grounds[0]
    assert (ground.kind, ground.holder_faction_id) == (
        GroundKind.BROKEN_PROMISE,
        CAUTIOUS_RIVAL,
    )
    assert ground.target_faction_id == WRATHFUL_RIVAL
    assert world.wars == []


def test_reduced_percent_scales_the_cost() -> None:
    world = make_world()
    world.truces = [_truce("truce_1", 99)]
    before = world.factions[WRATHFUL_RIVAL].reputation

    breach_agreements(world, SCENARIO, WRATHFUL_RIVAL, PLAYER, cost_percent=50)

    expected = TUNING.breach_reputation_cost * 50 // 100
    assert world.factions[WRATHFUL_RIVAL].reputation == before - expected


def test_breach_without_agreements_costs_nothing() -> None:
    world = make_world()
    before = world.factions[WRATHFUL_RIVAL].model_copy(deep=True)

    events = breach_agreements(world, SCENARIO, WRATHFUL_RIVAL, PLAYER)

    assert events == []
    assert world.factions[WRATHFUL_RIVAL] == before
    assert world.oathbreakers == []


def test_declaring_war_inside_a_truce_routes_through_the_breach() -> None:
    world = make_world()
    add_warning(world, WRATHFUL_RIVAL, PLAYER)
    world.truces = [_truce("truce_1", 99)]
    world = queue_npc_order(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )

    result = run_phase(DiplomacyPhase(), world)

    assert result.world.truces == []
    assert [mark.faction_id for mark in result.world.oathbreakers] == [WRATHFUL_RIVAL]


def test_apply_breach_consequences_marks_oathbreaker_and_charges_standing() -> None:
    world = make_world()
    before = world.factions[WRATHFUL_RIVAL].model_copy(deep=True)

    apply_breach_consequences(world, SCENARIO, WRATHFUL_RIVAL)
    apply_breach_consequences(world, SCENARIO, WRATHFUL_RIVAL)

    after = world.factions[WRATHFUL_RIVAL]
    assert after.reputation == before.reputation - 2 * TUNING.breach_reputation_cost
    assert after.stability == before.stability - 2 * TUNING.breach_stability_cost
    assert [mark.faction_id for mark in world.oathbreakers] == [WRATHFUL_RIVAL]


def test_grant_broken_promise_ground_gives_holder_a_ground() -> None:
    world = make_world()

    grant_broken_promise_ground(world, SCENARIO, PLAYER, WRATHFUL_RIVAL)

    ground = world.grounds[0]
    assert (ground.kind, ground.holder_faction_id) == (
        GroundKind.BROKEN_PROMISE,
        PLAYER,
    )
    assert ground.target_faction_id == WRATHFUL_RIVAL


def test_grant_broken_promise_ground_skips_destroyed_holder() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].is_destroyed = True

    grant_broken_promise_ground(world, SCENARIO, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    assert world.grounds == []
