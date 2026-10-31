import pytest
from app.engine.ai.headless import (
    FLAG_BANKRUPTCY,
    FLAG_ENDLESS_WAR,
    FLAG_PAUSED,
    FLAG_SNOWBALL,
    FLAG_STAGNATION,
    FLAG_UNREST,
    OBSERVER_FACTION_ID,
    run_headless,
)
from app.models.world_player import PlayerRuler
from strategy_contracts.examples import load_three_crowns_expanded

SCENARIO = load_three_crowns_expanded()
RULER = PlayerRuler(
    name="Valdren", trait_ids=["honorable", "cautious"], ambition_ids=["ambition_peace"]
)
SHORT_TURNS = 24
SHORT_SEEDS = (11, 12)
LONG_TURNS = 120
LONG_SEEDS = (1, 2, 3, 4, 5)
# NOTE: wars end through AI peace, but wars still run long enough to drain
# stability and gold first, so these two remain until the AI also uses the
# economy and alliance orders.
KNOWN_LIMITATION_FLAGS = {FLAG_UNREST, FLAG_BANKRUPTCY}
FORBIDDEN_FLAGS = {FLAG_SNOWBALL, FLAG_STAGNATION, FLAG_PAUSED, FLAG_ENDLESS_WAR}


def _real_treasuries(report) -> dict[str, int]:
    return {
        faction_id: treasury
        for faction_id, treasury in report.samples[-1].treasury_by_faction.items()
        if faction_id != OBSERVER_FACTION_ID
    }


@pytest.mark.parametrize("seed", SHORT_SEEDS)
def test_short_runs_complete_without_snowball_stagnation_or_pauses(seed: int) -> None:
    report = run_headless(SCENARIO, seed, SHORT_TURNS, RULER)

    assert report.turns_run == SHORT_TURNS
    assert not FORBIDDEN_FLAGS & set(report.flags)
    assert sum(sample.planned_orders for sample in report.samples) > 0
    assert sum(1 for gold in _real_treasuries(report).values() if gold > 0) >= 2


def _same_traits_scenario():
    scenario = SCENARIO.model_copy(deep=True)
    for leader in scenario.leaders:
        if leader.faction_id in ("house_carrow", "house_dunwick"):
            leader.trait_ids = ["proud", "cautious"]
    return scenario


def test_rulers_with_the_same_traits_do_not_act_identically() -> None:
    report = run_headless(_same_traits_scenario(), 3, SHORT_TURNS, RULER)

    carrow = report.order_fingerprints["house_carrow"]
    dunwick = report.order_fingerprints["house_dunwick"]
    assert carrow != dunwick


@pytest.mark.headless_long
@pytest.mark.parametrize("seed", LONG_SEEDS)
def test_long_runs_only_show_the_known_balance_flags(seed: int) -> None:
    report = run_headless(SCENARIO, seed, LONG_TURNS, RULER)

    assert report.turns_run == LONG_TURNS
    assert not FORBIDDEN_FLAGS & set(report.flags)
    assert set(report.flags) <= KNOWN_LIMITATION_FLAGS
