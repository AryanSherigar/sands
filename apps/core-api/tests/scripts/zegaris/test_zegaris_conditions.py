import pytest
from scripts.zegaris import combat
from zegaris_sim import get, initial_state, put, run_turn

SECRET_WORDS = (
    "twin",
    "children",
    "sun priestess",
    "immortal",
    "not human",
    "summoned",
    "puppet",
)


def advance(state, path, value):
    return run_turn(put(state, path, value))[0]


def test_the_tithe_runs_only_in_order() -> None:
    state = initial_state()
    for step, stage in (
        ("hired", "hired"),
        ("hauling", "hauling"),
        ("eclipse", "eclipse"),
        ("aftermath", "aftermath"),
    ):
        state = advance(state, "intent.tithe_step", step)
        assert get(state, "world.tithe") == stage
        assert get(state, "intent.tithe_step") == ""


@pytest.mark.parametrize("step", ["hauling", "eclipse", "aftermath"])
def test_a_skipped_step_is_discarded(step: str) -> None:
    state = advance(initial_state(), "intent.tithe_step", step)
    assert get(state, "world.tithe") == "offered"
    assert get(state, "intent.tithe_step") == ""


def test_the_secret_is_withheld_before_the_eclipse() -> None:
    for stage in ("offered", "hired", "hauling"):
        state = put(initial_state(), "world.tithe", stage)
        _, fired = run_turn(state)
        text = " ".join(item.narrator_instruction for item in fired).lower()
        assert not any(word in text for word in SECRET_WORDS), stage


def test_the_secret_is_told_once_the_eclipse_is_reached() -> None:
    state = put(initial_state(), "world.tithe", "eclipse")
    _, fired = run_turn(state)
    text = " ".join(item.narrator_instruction for item in fired).lower()
    assert "twins" in text and "do not know what rescue is" in text


def test_the_promenade_is_guarded_unless_escorted() -> None:
    state = initial_state("amber_promenade")
    assert any("Promenade" in item.narrator_instruction for item in run_turn(state)[1])
    escorted = put(state, "world.access", "escort")
    assert not any(
        "Promenade" in item.narrator_instruction for item in run_turn(escorted)[1]
    )


def test_an_unbadged_player_is_stopped_at_the_gate() -> None:
    state = initial_state("gate_of_the_unsworn")
    assert any("Gate" in item.narrator_instruction for item in run_turn(state)[1])
    badged = advance(state, "intent.access_step", "badge")
    assert get(badged, "world.access") == "badge"


def test_zegaris_stops_guarding_tiers_once_it_is_hunting_the_player() -> None:
    state = put(initial_state("amber_promenade"), "world.tithe", "aftermath")
    fired = run_turn(state)[1]
    assert not any("forbidden" in item.narrator_instruction for item in fired)


def test_the_shaft_keeps_the_soldiers_fate_open() -> None:
    state = put(initial_state("fissure_depths"), "quests.retrieval.stage", "accepted")
    text = " ".join(item.narrator_instruction for item in run_turn(state)[1])
    assert "NEVER confirm" in text and "recover_body" in text


def test_every_encounter_is_survivable_and_ends_nothing() -> None:
    for encounter in combat.encounters():
        outcomes = encounter["outcomes"]
        assert all(outcome["kind"] == "recover" for outcome in outcomes)
        assert encounter["fallback_outcome_id"] in {item["id"] for item in outcomes}
