from app.engine.hashing import world_hash
from app.engine.proclamations.modifiers import active_modifier
from strategy_contracts.enums import TaxRate
from strategy_contracts.proclamation import (
    ActiveProclamation,
    ProclamationBurden,
    ProclamationDomain,
)
from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    make_army,
    make_faction,
    make_region,
    make_world,
    run_economy,
)


def _edict(modifiers: dict[str, int], remaining: int = 4) -> ActiveProclamation:
    return ActiveProclamation(
        id="proc_0_test",
        legal_summary="Test edict.",
        domain=ProclamationDomain.MARTIAL_LEVIES,
        burden=ProclamationBurden.MODERATE,
        enacted_turn=0,
        remaining_turns=remaining,
        immediate_deltas={},
        ongoing_modifiers=modifiers,
    )


def _world(modifiers: dict[str, int], remaining: int = 4, **region: object):
    world = make_world(
        regions=[
            make_region("home", PLAYER, **region),
            make_region("rival_home", RIVAL, **region),
        ],
        factions=[
            make_faction(PLAYER, is_player=True, tax_rate=TaxRate.NORMAL),
            make_faction(RIVAL, tax_rate=TaxRate.NORMAL),
        ],
        armies=[make_army("army_a", PLAYER)],
    )
    world.active_proclamation = _edict(modifiers, remaining)
    return world


def test_an_edict_binds_only_the_player() -> None:
    world = _world({"unrest_per_turn": 3})

    assert active_modifier(world, PLAYER, "unrest_per_turn") == 3
    assert active_modifier(world, RIVAL, "unrest_per_turn") == 0
    assert active_modifier(world, PLAYER, "missing_key") == 0


def test_an_expired_or_missing_edict_changes_nothing() -> None:
    world = _world({"unrest_per_turn": 3}, remaining=0)
    assert active_modifier(world, PLAYER, "unrest_per_turn") == 0
    world.active_proclamation = None
    assert active_modifier(world, PLAYER, "unrest_per_turn") == 0


def test_the_unrest_modifier_moves_the_players_regions_every_turn() -> None:
    plain = run_economy(_world({}, unrest=20))
    edict = run_economy(_world({"unrest_per_turn": 3}, unrest=20))

    assert edict.world.regions["home"].unrest == plain.world.regions["home"].unrest + 3
    assert (
        edict.world.regions["rival_home"].unrest
        == plain.world.regions["rival_home"].unrest
    )


def test_the_tax_modifier_raises_player_income_only() -> None:
    plain = run_economy(_world({}))
    edict = run_economy(_world({"tax_percent_points": 20}))

    plain_gain = plain.world.factions[PLAYER].treasury
    edict_gain = edict.world.factions[PLAYER].treasury
    assert edict_gain > plain_gain
    assert edict.world.factions[RIVAL].treasury == plain.world.factions[RIVAL].treasury


def test_the_manpower_modifier_speeds_up_the_players_refill_within_the_cap() -> None:
    plain = run_economy(_world({}, population=1000, manpower=0))
    edict = run_economy(
        _world({"manpower_regen_percent": 50}, population=1000, manpower=0)
    )

    assert edict.world.regions["home"].manpower > plain.world.regions["home"].manpower
    assert (
        edict.world.regions["rival_home"].manpower
        == plain.world.regions["rival_home"].manpower
    )


def test_the_same_turn_with_the_same_edict_hashes_identically() -> None:
    world = _world({"unrest_per_turn": 3, "tax_percent_points": 15}, unrest=20)

    first = run_economy(world)
    second = run_economy(world)

    assert world_hash(first.world) == world_hash(second.world)
