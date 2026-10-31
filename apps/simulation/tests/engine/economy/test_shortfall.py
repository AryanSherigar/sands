from app.engine.economy.phase import EconomyPhase
from app.engine.economy.reasons import SHORTFALL_DEFAULT, SHORTFALL_TAKE_LOAN
from app.engine.phases import ScenePause
from app.engine.pipeline import run_turn
from app.models.orders import DeclareDefaultOrder, TakeLoanOrder
from app.models.world_events import PHASE_ORDER, PhaseName, TurnStatus
from strategy_contracts.scene import ChoiceOutcome, ProseOnlyOutcome, SceneType

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
    queued,
    run_economy,
)
from tests.engine.toy_phases import ToyPhase

# Income 50 against 120 upkeep: a 70 gold shortfall, with credit available.
INCOME_WEALTH = 50
SHORTFALL = 70


def _world(is_player: bool = True, treasury: int = 0, wealth: int = INCOME_WEALTH):
    regions = [make_region("home", PLAYER, wealth=wealth)] if wealth else []
    return make_world(
        regions=regions,
        factions=[
            make_faction(PLAYER, treasury=treasury, is_player=is_player),
            make_faction(RIVAL),
        ],
        armies=[
            make_army("army_a", PLAYER, troops={"infantry": 400}),
            make_army("army_b", PLAYER, troops={"infantry": 800}),
        ],
    )


def _do_nothing(world, rng, context) -> None:
    return None


def _resumed(world):
    world.progress.pending_scene_id = SCENE_ID
    return world


def _choose(option_id: str):
    return {SCENE_ID: ChoiceOutcome(option_id=option_id)}


def test_a_shortfall_pauses_the_turn_and_asks_the_player() -> None:
    result = run_economy(_world())
    assert result.pause == ScenePause(SceneType.EVENT, (PLAYER,))
    assert result.events == []


def test_taking_the_loan_covers_the_gap_and_keeps_everyone_paid() -> None:
    outcomes = _choose(SHORTFALL_TAKE_LOAN)
    result = run_economy(_resumed(_world()), outcomes=outcomes)
    faction = result.world.factions[PLAYER]
    [event] = events_of(result, "shortfall_resolved")
    assert result.pause is None
    assert [loan.principal for loan in faction.loans] == [SHORTFALL]
    assert faction.treasury == 0
    assert all(army.unpaid_turns == 0 for army in result.world.armies.values())
    assert event.cause.inputs == {"shortfall": SHORTFALL, "loan_granted": SHORTFALL}
    assert faction.credit_strikes == 0


def test_defaulting_leaves_armies_unpaid_and_marks_the_faction() -> None:
    outcomes = _choose(SHORTFALL_DEFAULT)
    result = run_economy(_resumed(_world()), outcomes=outcomes)
    faction = result.world.factions[PLAYER]
    assert faction.loans == []
    assert faction.credit_strikes == 1
    assert result.world.armies["army_b"].unpaid_turns == 1


def test_the_players_choice_costs_an_order_from_next_turns_budget() -> None:
    for option in (SHORTFALL_TAKE_LOAN, SHORTFALL_DEFAULT):
        result = run_economy(_resumed(_world()), outcomes=_choose(option))
        assert result.world.factions[PLAYER].orders_debt == 1


def test_an_unrelated_outcome_counts_as_walking_away_and_defaults() -> None:
    outcomes = {SCENE_ID: ProseOnlyOutcome()}
    result = run_economy(_resumed(_world()), outcomes=outcomes)
    assert result.world.factions[PLAYER].credit_strikes == 1


def test_an_unknown_option_counts_as_walking_away_and_defaults() -> None:
    result = run_economy(_resumed(_world()), outcomes=_choose("print_money"))
    assert result.world.factions[PLAYER].loans == []
    assert result.world.factions[PLAYER].credit_strikes == 1


def test_a_pre_declared_default_needs_no_pause_and_costs_no_extra_order() -> None:
    order = queued(DeclareDefaultOrder(faction_id=PLAYER))
    result = run_economy(_world(), orders=[order])
    assert result.pause is None
    assert result.world.factions[PLAYER].orders_debt == 0
    assert result.world.factions[PLAYER].credit_strikes == 1


def test_a_pre_queued_loan_that_covers_everything_avoids_the_pause() -> None:
    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=SHORTFALL))
    result = run_economy(_world(), orders=[order])
    assert result.pause is None
    assert events_of(result, "shortfall_resolved") == []
    assert result.world.factions[PLAYER].credit_strikes == 0


def test_a_pre_queued_loan_that_is_too_small_still_pauses() -> None:
    order = queued(TakeLoanOrder(faction_id=PLAYER, amount=10))
    assert run_economy(_world(), orders=[order]).pause is not None


def test_a_rival_takes_the_loan_by_itself_when_it_can() -> None:
    result = run_economy(_world(is_player=False))
    assert result.pause is None
    assert [loan.principal for loan in result.world.factions[PLAYER].loans] == [
        SHORTFALL
    ]
    assert result.world.factions[PLAYER].orders_debt == 0


def test_a_player_with_no_credit_defaults_without_being_asked() -> None:
    result = run_economy(_world(wealth=0))
    assert result.pause is None
    assert result.world.factions[PLAYER].credit_strikes == 1
    assert result.world.factions[PLAYER].orders_debt == 0


def test_a_player_in_a_world_without_loans_defaults_without_being_asked() -> None:
    result = run_economy(_world(), make_scenario(is_loans_enabled=False))
    assert result.pause is None
    assert result.world.factions[PLAYER].credit_strikes == 1


def test_enough_money_means_no_question_at_all() -> None:
    result = run_economy(_world(treasury=200))
    assert result.pause is None
    assert events_of(result, "shortfall_resolved") == []


def test_the_pause_and_resume_work_through_the_turn_pipeline() -> None:
    scenario = make_scenario()
    phases = {name: ToyPhase(name, _do_nothing) for name in PHASE_ORDER}
    phases[PhaseName.ECONOMY] = EconomyPhase()
    paused = run_turn(_world(), scenario, [], phases, {}, {})
    assert paused.status is TurnStatus.PAUSED
    assert paused.world.progress.phase is PhaseName.ECONOMY
    resumable = paused.world.model_copy(deep=True)
    resumable.progress.pending_scene_id = SCENE_ID
    outcomes = _choose(SHORTFALL_TAKE_LOAN)
    resumed = run_turn(resumable, scenario, [], phases, outcomes, {})
    assert resumed.status is TurnStatus.RESOLVED
    assert resumed.world.factions[PLAYER].loans[0].principal == SHORTFALL
