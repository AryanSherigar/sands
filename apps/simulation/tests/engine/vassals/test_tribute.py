from app.engine.vassals.signing import sign_vassalage
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_state import WorldState
from strategy_contracts.terms import VassalTerm

from tests.engine.economy.builders import (
    PLAYER,
    RIVAL,
    SCENE_ID,
    events_of,
    make_army,
    make_faction,
    make_region,
    make_scenario,
    make_world,
    run_economy,
)
from tests.engine.vassals.builders import make_vassal_term

START_TREASURY = 100
INCOME = 100


def _world(
    tribute: int, vassal_treasury: int = START_TREASURY, armies=()
) -> WorldState:
    world = make_world(
        regions=[
            make_region("home", PLAYER, wealth=INCOME),
            make_region("fief", RIVAL, wealth=INCOME),
        ],
        factions=[
            make_faction(PLAYER, treasury=START_TREASURY),
            make_faction(RIVAL, treasury=vassal_treasury),
        ],
        armies=armies,
    )
    world.vassal_ruleset = 1
    term: VassalTerm = make_vassal_term(PLAYER, RIVAL, tribute=tribute)
    sign_vassalage(world, make_scenario(), term, SCENE_ID)
    return world


def test_overlord_receives_the_share_of_vassal_income() -> None:
    result = run_economy(_world(tribute=20))

    assert result.world.factions[PLAYER].treasury == START_TREASURY + INCOME + 20
    assert result.world.factions[RIVAL].treasury == START_TREASURY + INCOME - 20
    assert len(events_of(result, "tribute_paid")) == 1


def test_tribute_never_exceeds_vassal_treasury() -> None:
    army = make_army("army_b", RIVAL, troops={"infantry": 900})

    result = run_economy(_world(tribute=20, vassal_treasury=0, armies=[army]))

    paid = events_of(result, "tribute_paid")[0].cause.inputs["amount"]
    assert paid == result.world.factions[PLAYER].treasury - START_TREASURY - INCOME
    assert result.world.factions[RIVAL].treasury >= 0
    assert paid < 20


def test_zero_share_pays_nothing() -> None:
    result = run_economy(_world(tribute=0))

    assert events_of(result, "tribute_paid") == []
    assert result.world.factions[PLAYER].treasury == START_TREASURY + INCOME


def test_ended_vassalage_pays_nothing() -> None:
    world = _world(tribute=20)
    world.commitments[0].status = CommitmentStatus.EXPIRED

    result = run_economy(world)

    assert events_of(result, "tribute_paid") == []


def test_legacy_world_pays_nothing() -> None:
    world = _world(tribute=20)
    world.vassal_ruleset = 0

    assert events_of(run_economy(world), "tribute_paid") == []


def test_a_paused_pass_collects_no_tribute() -> None:
    world = _world(tribute=20)
    world.factions[PLAYER].is_player = True
    world.factions[PLAYER].treasury = 0
    world.armies = {
        "army_a": make_army("army_a", PLAYER, troops={"infantry": 1200}),
    }

    result = run_economy(world)

    assert result.pause is not None
    assert result.world.factions[RIVAL].treasury == START_TREASURY
