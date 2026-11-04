import pytest
from engine_sim import Engine, apply, get, new_engine
from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.characters import CHARACTERS
from scripts.reincarnated_aristocrat.conditions.training import stat_cap
from scripts.reincarnated_aristocrat.ids import entity_id
from scripts.reincarnated_aristocrat.stats import TRAINABLE_STATS

RETAINERS = [spec for spec in CHARACTERS if spec.is_recruitable]
RICH_FUNDS = 900
FULL_RESOURCES = 100


def attr(slug: str, name: str) -> str:
    return f"{entity_id(slug)}.{name}"


def put(engine: Engine, path: str, value: object) -> None:
    engine.state = apply(engine.state, path, "set", value)


def trainer(slug: str = "ritsu") -> Engine:
    engine = new_engine()
    put(engine, attr(slug, "is_recruited"), True)
    return engine


def request(engine: Engine, slug: str, stat: str) -> None:
    put(engine, "intent.train_who", slug)
    put(engine, "intent.train_stat", stat)
    engine.turn()


def test_a_low_stat_gains_two_and_the_house_pays() -> None:
    engine = trainer()
    request(engine, "ritsu", "leadership")
    assert get(engine.state, attr("ritsu", "leadership")) == 30 + balance.TRAIN_BIG_GAIN
    assert get(engine.state, "funds") == 60 - balance.TRAIN_BIG_COST[0]
    assert get(engine.state, "resources") == 40 - balance.TRAIN_BIG_COST[1]
    assert get(engine.state, attr("ritsu", "has_trained")) is True
    assert get(engine.state, "intent.train_who") == ""
    assert get(engine.state, "intent.train_stat") == ""
    assert get(engine.state, "army_strength") == 5 + balance.ARMY_PER_TRAINING


def test_a_high_stat_gains_one_for_a_higher_price() -> None:
    engine = trainer()
    put(engine, attr("ritsu", "prowess"), 70)
    request(engine, "ritsu", "prowess")
    assert get(engine.state, attr("ritsu", "prowess")) == 71
    assert get(engine.state, "funds") == 60 - balance.TRAIN_SMALL_COST[0]


def test_politics_training_does_not_change_the_army() -> None:
    engine = trainer()
    request(engine, "ritsu", "politics")
    assert get(engine.state, "army_strength") == 5


def test_a_stat_one_below_its_cap_gains_one_not_two() -> None:
    engine = trainer()
    cap = stat_cap(RETAINERS[0], "leadership")
    put(engine, attr("ritsu", "leadership"), cap - 1)
    request(engine, "ritsu", "leadership")
    assert get(engine.state, attr("ritsu", "leadership")) == cap


def test_a_stat_at_its_cap_gains_nothing_and_costs_nothing() -> None:
    engine = trainer()
    cap = stat_cap(RETAINERS[0], "leadership")
    put(engine, attr("ritsu", "leadership"), cap)
    request(engine, "ritsu", "leadership")
    assert get(engine.state, attr("ritsu", "leadership")) == cap
    assert get(engine.state, "funds") == 60
    assert get(engine.state, attr("ritsu", "has_trained")) is False
    assert any("learned all" in text for text in engine.instructions)


@pytest.mark.parametrize("setup", ["poor", "unrecruited", "already_trained"])
def test_training_that_cannot_happen_changes_nothing(setup: str) -> None:
    engine = trainer()
    if setup == "poor":
        put(engine, "funds", 3)
    if setup == "unrecruited":
        put(engine, attr("ritsu", "is_recruited"), False)
    if setup == "already_trained":
        put(engine, attr("ritsu", "has_trained"), True)
    before = get(engine.state, attr("ritsu", "leadership"))
    request(engine, "ritsu", "leadership")
    assert get(engine.state, attr("ritsu", "leadership")) == before
    assert get(engine.state, "intent.train_who") == ""
    assert any("cannot happen now" in text for text in engine.instructions)


@pytest.mark.parametrize("stat", TRAINABLE_STATS)
@pytest.mark.parametrize("spec", RETAINERS, ids=lambda spec: spec.slug)
def test_repeated_training_reaches_the_cap_and_never_overshoots_it(
    spec: object, stat: str
) -> None:
    engine = trainer(spec.slug)  # type: ignore[attr-defined]
    cap = stat_cap(spec, stat)  # type: ignore[arg-type]
    path = attr(spec.slug, stat)  # type: ignore[attr-defined]
    for _ in range(cap + 5):
        put(engine, "funds", RICH_FUNDS)
        put(engine, "resources", FULL_RESOURCES)
        put(engine, attr(spec.slug, "has_trained"), False)  # type: ignore[attr-defined]
        request(engine, spec.slug, stat)  # type: ignore[attr-defined]
        assert get(engine.state, path) <= cap
    assert get(engine.state, path) == cap
    training_rejections = [item for item in engine.rejected if item.startswith("T")]
    assert training_rejections == []
