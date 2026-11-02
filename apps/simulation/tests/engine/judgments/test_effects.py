import pytest
from app.engine.judgments.constants import (
    BASE_MERCY_SCORE,
    BASE_OPINION,
    MEMORY_KIND_PREFIX,
    MEMORY_WEIGHT,
    NUANCE_MERCY_SCORE,
    NUANCE_OPINION,
    WITNESS_GOVERNOR_SHIFT,
)
from app.engine.judgments.effects import apply_judgment
from app.engine.opinion import opinion_of
from strategy_contracts.judgment import (
    NUANCES_BY_VERDICT,
    JudgmentNuance,
    JudgmentOutcome,
    JudgmentVerdict,
)

from tests.engine.judgments.builders import (
    CAPTIVE_ID,
    GOVERNOR_ID,
    GOVERNOR_REGION,
    OTHER_GOVERNOR_ID,
    PLAYER,
    PLAYER_LEADER,
    RIVAL,
    RIVAL_LEADER,
    TURN,
    captive_pending,
    governor_pending,
    judgment_scenario,
    judgment_world,
)

ALL_PAIRS = [
    (verdict, nuance)
    for verdict, nuances in NUANCES_BY_VERDICT.items()
    for nuance in nuances
]


def _opinion(world) -> int:
    return opinion_of(world.leaders[RIVAL_LEADER], PLAYER_LEADER)


def _apply_captive(verdict: JudgmentVerdict, nuance: JudgmentNuance | None = None):
    world = judgment_world()
    scenario = judgment_scenario()
    events = apply_judgment(
        world,
        scenario,
        captive_pending(),
        JudgmentOutcome(verdict=verdict, nuance=nuance),
    )
    return world, scenario, events


@pytest.mark.parametrize(("verdict", "nuance"), ALL_PAIRS)
def test_every_verdict_nuance_pair_shifts_the_accused_leaders_opinion(
    verdict: JudgmentVerdict, nuance: JudgmentNuance
) -> None:
    world, _, _ = _apply_captive(verdict, nuance)
    assert _opinion(world) == BASE_OPINION[verdict] + NUANCE_OPINION[nuance]


@pytest.mark.parametrize(("verdict", "nuance"), ALL_PAIRS)
def test_every_verdict_nuance_pair_shifts_mercy_score(
    verdict: JudgmentVerdict, nuance: JudgmentNuance
) -> None:
    world, _, _ = _apply_captive(verdict, nuance)
    expected = BASE_MERCY_SCORE[verdict] + NUANCE_MERCY_SCORE.get(nuance, 0)
    assert world.leaders[RIVAL_LEADER].beliefs.mercy_score == expected


def test_release_frees_the_captive_and_counts_a_mercy_act() -> None:
    world, _, events = _apply_captive(JudgmentVerdict.RELEASE)
    assert world.prisoners == []
    assert world.player_profile.mercy_acts == 1
    assert world.player_profile.cruelty_acts == 0
    assert [event.kind for event in events] == [
        "prisoner_released",
        "judgment_pronounced",
    ]


def test_every_verdict_records_a_decaying_memory_on_the_accused_leader() -> None:
    world, _, _ = _apply_captive(JudgmentVerdict.EXILE)
    memory = world.leaders[RIVAL_LEADER].memories[-1]
    assert (memory.kind, memory.weight, memory.subject_id, memory.turn) == (
        f"{MEMORY_KIND_PREFIX}exile",
        MEMORY_WEIGHT,
        PLAYER_LEADER,
        TURN,
    )


def test_exile_removes_the_captive_without_an_atrocity() -> None:
    world, _, _ = _apply_captive(JudgmentVerdict.EXILE)
    assert world.prisoners == []
    assert world.coalition.atrocities.get(PLAYER, 0) == 0


def test_imprison_keeps_the_captive_in_custody() -> None:
    world, _, _ = _apply_captive(JudgmentVerdict.IMPRISON, JudgmentNuance.IN_CAPITAL)
    assert [item.id for item in world.prisoners] == [CAPTIVE_ID]
    assert world.prisoners[0].sentence_ends_turn is None


def test_for_a_term_sets_the_sentence_end_turn() -> None:
    world, scenario, _ = _apply_captive(
        JudgmentVerdict.IMPRISON, JudgmentNuance.FOR_A_TERM
    )
    assert world.prisoners[0].sentence_ends_turn == (
        TURN + scenario.tuning.judgments.sentence_turns
    )


def test_execute_counts_cruelty_records_an_atrocity_and_costs_reputation() -> None:
    world, scenario, _ = _apply_captive(JudgmentVerdict.EXECUTE, JudgmentNuance.SWIFTLY)
    cost = scenario.tuning.peace.atrocity_reputation_cost
    assert world.prisoners == []
    assert world.player_profile.cruelty_acts == 1
    assert world.coalition.atrocities[PLAYER] == 1
    assert world.factions[PLAYER].reputation == -cost


def test_execute_quietly_skips_the_atrocity_and_halves_the_reputation_cost() -> None:
    world, scenario, _ = _apply_captive(JudgmentVerdict.EXECUTE, JudgmentNuance.QUIETLY)
    cost = scenario.tuning.peace.atrocity_reputation_cost
    assert world.coalition.atrocities.get(PLAYER, 0) == 0
    assert world.factions[PLAYER].reputation == -(cost // 2)


def test_execute_publicly_records_an_extra_atrocity() -> None:
    world, _, _ = _apply_captive(JudgmentVerdict.EXECUTE, JudgmentNuance.PUBLICLY)
    assert world.coalition.atrocities[PLAYER] == 2


def test_with_fine_ransoms_a_captive_for_gold() -> None:
    world = judgment_world()
    scenario = judgment_scenario()
    price = scenario.tuning.peace.ransom_gold_per_character
    world.factions[RIVAL].treasury = price + 50
    start = world.factions[PLAYER].treasury
    apply_judgment(
        world,
        scenario,
        captive_pending(),
        JudgmentOutcome(
            verdict=JudgmentVerdict.RELEASE, nuance=JudgmentNuance.WITH_FINE
        ),
    )
    assert world.factions[PLAYER].treasury == start + price
    assert world.prisoners == []


def test_with_fine_is_capped_at_the_origin_treasury() -> None:
    world = judgment_world()
    scenario = judgment_scenario()
    world.factions[RIVAL].treasury = 7
    start = world.factions[PLAYER].treasury
    apply_judgment(
        world,
        scenario,
        captive_pending(),
        JudgmentOutcome(
            verdict=JudgmentVerdict.RELEASE, nuance=JudgmentNuance.WITH_FINE
        ),
    )
    assert world.factions[PLAYER].treasury == start + 7
    assert world.factions[RIVAL].treasury == 0
    assert world.prisoners == []


def test_a_stale_prisoner_applies_nothing() -> None:
    world = judgment_world()
    world.prisoners = []
    before = world.model_copy(deep=True)
    events = apply_judgment(
        world,
        judgment_scenario(),
        captive_pending(),
        JudgmentOutcome(verdict=JudgmentVerdict.EXECUTE),
    )
    assert events == []
    assert world == before


def _apply_governor(verdict: JudgmentVerdict, nuance: JudgmentNuance | None = None):
    world = judgment_world()
    events = apply_judgment(
        world,
        judgment_scenario(),
        governor_pending(),
        JudgmentOutcome(verdict=verdict, nuance=nuance),
    )
    return world, events


@pytest.mark.parametrize(
    "verdict",
    [JudgmentVerdict.EXILE, JudgmentVerdict.IMPRISON, JudgmentVerdict.EXECUTE],
)
def test_removing_verdicts_clear_the_governors_post(verdict: JudgmentVerdict) -> None:
    world, _ = _apply_governor(verdict)
    assert GOVERNOR_ID not in world.governors
    assert world.regions[GOVERNOR_REGION].governor_id is None


def test_releasing_a_governor_keeps_the_post() -> None:
    world, _ = _apply_governor(JudgmentVerdict.RELEASE)
    assert GOVERNOR_ID in world.governors
    assert world.regions[GOVERNOR_REGION].governor_id == GOVERNOR_ID


@pytest.mark.parametrize("verdict", list(JudgmentVerdict))
def test_other_governors_shift_by_the_witness_table(verdict: JudgmentVerdict) -> None:
    world, _ = _apply_governor(verdict)
    assert world.governors[OTHER_GOVERNOR_ID].opinion_of_ruler == (
        10 + WITNESS_GOVERNOR_SHIFT[verdict]
    )


def test_a_governor_judgment_does_not_touch_a_rival_leaders_opinion() -> None:
    world, _ = _apply_governor(JudgmentVerdict.EXECUTE)
    assert _opinion(world) == 0
    assert world.player_profile.cruelty_acts == 1


def test_a_governor_fine_pays_the_player_treasury() -> None:
    world = judgment_world()
    scenario = judgment_scenario()
    start = world.factions[PLAYER].treasury
    apply_judgment(
        world,
        scenario,
        governor_pending(),
        JudgmentOutcome(
            verdict=JudgmentVerdict.RELEASE, nuance=JudgmentNuance.WITH_FINE
        ),
    )
    assert world.factions[PLAYER].treasury == (
        start + scenario.tuning.peace.ransom_gold_per_character
    )


def test_a_stale_governor_applies_nothing() -> None:
    world = judgment_world()
    del world.governors[GOVERNOR_ID]
    before = world.model_copy(deep=True)
    events = apply_judgment(
        world,
        judgment_scenario(),
        governor_pending(),
        JudgmentOutcome(verdict=JudgmentVerdict.EXECUTE),
    )
    assert events == []
    assert world == before
