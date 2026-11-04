import pytest
from engine_sim import Engine, apply, evaluate, get, new_engine
from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.builder import build
from scripts.reincarnated_aristocrat.ids import entity_id

ENDINGS = sorted(build().end_conditions, key=lambda ending: ending.priority)
STRATEGISTS = ("rosell", "mireille")


def attr(slug: str, name: str) -> str:
    return f"{entity_id(slug)}.{name}"


def put(engine: Engine, **values: object) -> None:
    for path, value in values.items():
        engine.state = apply(engine.state, path.replace("__", "."), "set", value)


def first_ending(engine: Engine) -> str | None:
    for ending in ENDINGS:
        if evaluate(ending.condition_expression, engine.state):
            return ending.outcome_title
    return None


def ready() -> Engine:
    engine = new_engine()
    put(
        engine,
        beats__couran_called=True,
        standing=balance.WIN_STANDING,
        control=balance.WIN_CONTROL,
        resources=balance.WIN_RESOURCES,
        funds=balance.WIN_FUNDS,
        army_strength=balance.WIN_ARMY,
        time__recruits=balance.WIN_RECRUITS,
        sheet__competence=balance.WIN_COMPETENCE,
    )
    for slug in ("ritsu", "charlotte", "rosell"):
        engine.state = apply(engine.state, attr(slug, "is_recruited"), "set", True)
    return engine


def test_a_new_run_matches_no_ending() -> None:
    assert first_ending(new_engine()) is None


def test_a_ready_house_becomes_lord_of_canarre() -> None:
    assert first_ending(ready()) == "Lord of Canarre"


def test_a_feared_ready_house_gets_the_fear_ending_instead() -> None:
    engine = ready()
    put(
        engine,
        sheet__fear=balance.FEAR_WIN_FEAR,
        sheet__goodwill=balance.FEAR_WIN_GOODWILL,
    )
    assert first_ending(engine) == "The Lord Everyone Obeys"


@pytest.mark.parametrize(
    "change",
    [
        {"beats__couran_called": False},
        {"standing": balance.WIN_STANDING - 1},
        {"control": balance.WIN_CONTROL - 1},
        {"resources": balance.WIN_RESOURCES - 1},
        {"funds": balance.WIN_FUNDS - 1},
        {"army_strength": balance.WIN_ARMY - 1},
        {"time__recruits": balance.WIN_RECRUITS - 1},
        {"sheet__competence": balance.WIN_COMPETENCE - 1},
    ],
)
def test_missing_any_threshold_blocks_the_win(change: dict[str, object]) -> None:
    engine = ready()
    put(engine, **change)
    assert first_ending(engine) != "Lord of Canarre"


@pytest.mark.parametrize("slug", ["ritsu", "charlotte"])
def test_the_commander_and_the_mage_are_required(slug: str) -> None:
    engine = ready()
    engine.state = apply(engine.state, attr(slug, "is_recruited"), "set", False)
    assert first_ending(engine) != "Lord of Canarre"


def test_either_strategist_will_do_but_one_is_required() -> None:
    engine = ready()
    engine.state = apply(engine.state, attr("rosell", "is_recruited"), "set", False)
    engine.state = apply(engine.state, attr("mireille", "is_recruited"), "set", True)
    assert first_ending(engine) == "Lord of Canarre"
    engine.state = apply(engine.state, attr("mireille", "is_recruited"), "set", False)
    assert first_ending(engine) != "Lord of Canarre"


def test_an_active_betrayal_warning_blocks_the_win() -> None:
    engine = ready()
    engine.state = apply(engine.state, attr("lysia", "betrayal_risk"), "set", True)
    assert first_ending(engine) != "Lord of Canarre"


@pytest.mark.parametrize(
    ("change", "title"),
    [
        ({"beats__coup": True}, "The Household Turns"),
        ({"time__debt_months": balance.RUIN_MONTHS}, "The Empty Treasury"),
        ({"time__low_resources": balance.RUIN_MONTHS}, "A Hungry Winter"),
        ({"time__low_control": balance.RUIN_MONTHS}, "The Valley Rises"),
        ({"time__turns": balance.TIMEOUT_TURNS}, "Lamberk Endures"),
    ],
)
def test_each_failure_state_has_its_own_ending(
    change: dict[str, object], title: str
) -> None:
    engine = new_engine()
    put(engine, **change)
    assert first_ending(engine) == title


def test_a_coup_overrides_a_win() -> None:
    engine = ready()
    put(engine, beats__coup=True)
    assert first_ending(engine) == "The Household Turns"


def test_a_weak_army_loses_once_the_grace_period_after_couran_ends() -> None:
    engine = new_engine()
    put(engine, beats__couran_called=True, army_strength=balance.COLLAPSE_ARMY - 1)
    put(engine, time__clock_days=balance.COURAN_DAY + balance.COLLAPSE_GRACE_DAYS - 1)
    assert first_ending(engine) is None
    put(engine, time__clock_days=balance.COURAN_DAY + balance.COLLAPSE_GRACE_DAYS)
    assert first_ending(engine) == "Too Few Swords"


def test_the_outcome_tags_are_win_for_the_two_wins_and_lose_otherwise() -> None:
    tags = {ending.outcome_title: ending.outcome_tag for ending in ENDINGS}
    assert tags["Lord of Canarre"] == "win"
    assert tags["The Lord Everyone Obeys"] == "win"
    assert sum(tag == "lose" for tag in tags.values()) == 6


def test_only_the_fear_ending_is_secret() -> None:
    secret = [ending.outcome_title for ending in ENDINGS if ending.is_secret]
    assert secret == ["The Lord Everyone Obeys"]


def test_a_house_that_does_nothing_loses_to_couran_but_not_before() -> None:
    engine = new_engine()
    engine.run(120)
    assert first_ending(engine) is None
    engine.run(80)
    assert first_ending(engine) == "Too Few Swords"
    assert get(engine.state, "time.turns") == 200
