from app.engine.coalitions.phase import tick_coalitions
from app.engine.hashing import canonical_world_json, world_hash
from app.models.world_state import WorldState

from tests.engine.coalitions.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_threat_world,
)

TURNS = 4


def _scripted_run() -> WorldState:
    world = make_threat_world()
    world.coalition.atrocities[PLAYER] = 60
    for _ in range(TURNS):
        world.clock.turn += 1
        tick_coalitions(world, SCENARIO)
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=CAUTIOUS_RIVAL)
    tick_coalitions(world, SCENARIO)
    return world


def test_scripted_coalition_run_replays_with_identical_hashes() -> None:
    first, second = _scripted_run(), _scripted_run()

    assert world_hash(first) == world_hash(second)
    assert canonical_world_json(first) == canonical_world_json(second)


def test_a_legacy_world_hash_ignores_coalition_ledgers() -> None:
    world = make_threat_world()
    world.coalition_ruleset = 0

    assert "coalition" not in canonical_world_json(world)


def _appease_run(amount: int) -> WorldState:
    from app.engine.diplomacy.phase import DiplomacyPhase
    from app.models.orders import AppeaseCoalitionOrder
    from strategy_contracts.coalition import GoldOffer

    from tests.engine.coalitions.builders import make_coalition_world
    from tests.engine.diplomacy.builders import queue_npc_order, run_phase

    world = make_coalition_world()
    world.factions[PLAYER].treasury = 1000
    order = AppeaseCoalitionOrder(
        faction_id=PLAYER, member_id=WRATHFUL_RIVAL, offer=GoldOffer(amount=amount)
    )
    return run_phase(DiplomacyPhase(), queue_npc_order(world, SCENARIO, order)).world


def test_appease_run_replays_with_identical_hashes() -> None:
    for amount in (1, 500):
        first, second = _appease_run(amount), _appease_run(amount)

        assert world_hash(first) == world_hash(second)
        assert canonical_world_json(first) == canonical_world_json(second)


def test_accepted_and_refused_appease_leave_different_worlds() -> None:
    assert world_hash(_appease_run(1)) != world_hash(_appease_run(500))


def test_a_world_without_appease_activity_hashes_without_its_keys() -> None:
    document = canonical_world_json(make_threat_world())

    assert "appease_cooldowns" not in document
    assert "rejoin_lockouts" not in document
