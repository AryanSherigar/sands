from engine_sim import Engine, apply, get, new_engine
from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.ids import entity_id

DUE_CLOCK = 15


def attr(slug: str, name: str) -> str:
    return f"{entity_id(slug)}.{name}"


def put(engine: Engine, path: str, value: object) -> None:
    engine.state = apply(engine.state, path, "set", value)


def retainer(slug: str, **values: object) -> Engine:
    engine = new_engine()
    put(engine, attr(slug, "is_recruited"), True)
    for name, value in values.items():
        put(engine, attr(slug, name), value)
    return engine


def month_with(engine: Engine, **sheet: object) -> None:
    for name, value in sheet.items():
        put(engine, f"sheet.{name}", value)
    put(engine, "time.clock_days", DUE_CLOCK)
    engine.turn()


def test_a_devoted_retainer_grows_more_loyal_under_a_kind_lord() -> None:
    engine = retainer("ritsu")
    month_with(engine, goodwill=70)
    assert get(engine.state, attr("ritsu", "loyalty")) == 40 + 1 + 1


def test_a_devoted_retainer_turns_on_a_cruel_lord() -> None:
    engine = retainer("ritsu")
    month_with(engine, goodwill=10)
    assert get(engine.state, attr("ritsu", "loyalty")) == 40 + 1 - 3


def test_an_ambitious_retainer_follows_a_competent_lord() -> None:
    engine = retainer("lysia")
    month_with(engine, competence=80)
    assert get(engine.state, attr("lysia", "loyalty")) == 40 + 2


def test_an_ambitious_retainer_grows_hungrier_when_the_lord_falters() -> None:
    engine = retainer("lysia")
    month_with(engine, competence=10)
    assert get(engine.state, attr("lysia", "loyalty")) == 40 - 2
    assert get(engine.state, attr("lysia", "ambition")) == 80 + 2


def test_a_timid_retainer_is_held_in_line_by_fear() -> None:
    engine = retainer("lysia")
    month_with(engine, fear=70)
    assert get(engine.state, attr("lysia", "ambition")) >= 80


def test_an_unrecruited_character_is_unaffected_by_the_month() -> None:
    engine = new_engine()
    month_with(engine, goodwill=100, competence=100)
    assert get(engine.state, attr("ritsu", "loyalty")) == 40


def test_unpaid_months_cost_every_retainer_loyalty() -> None:
    engine = retainer("ritsu")
    put(engine, "funds", 2)
    month_with(engine)
    assert get(engine.state, attr("ritsu", "loyalty")) < 40 + 1


def test_a_wavering_ambitious_retainer_is_warned_about_then_nudged() -> None:
    engine = retainer("lysia", loyalty=30)
    engine.turn()
    assert get(engine.state, attr("lysia", "betrayal_risk")) is True
    assert sum("wavering" in text for text in engine.instructions) == 1
    assert not any("remains restless" in text for text in engine.instructions)
    engine.turn()
    assert any("remains restless" in text for text in engine.instructions)


def test_a_steady_retainer_does_not_trigger_a_warning() -> None:
    engine = retainer("lysia", loyalty=60)
    engine.turn()
    assert get(engine.state, attr("lysia", "betrayal_risk")) is False


def test_a_retainer_who_recovers_loyalty_clears_the_risk() -> None:
    engine = retainer("lysia", loyalty=30)
    engine.turn()
    put(engine, attr("lysia", "loyalty"), balance.RECOVERY_LOYALTY)
    engine.turn()
    assert get(engine.state, attr("lysia", "betrayal_risk")) is False
    assert any("steadier" in text for text in engine.instructions)


def test_a_restless_retainer_eventually_leaves_with_some_coin() -> None:
    engine = retainer("mireille", betrayal_risk=True, loyalty=10)
    put(engine, "time.recruits", 3)
    put(engine, "army_strength", 20)
    put(engine, "sheet.competence", 50)
    engine.turn()
    assert get(engine.state, attr("mireille", "is_recruited")) is False
    assert get(engine.state, "time.recruits") == 2
    assert get(engine.state, "army_strength") == 20 - balance.ARMY_VALUE["mireille"]
    assert get(engine.state, "funds") == 60 - balance.BETRAYAL_FUNDS_LOSS
    assert get(engine.state, "beats.coup") is False


def test_a_betrayal_while_the_lord_is_weak_is_a_coup() -> None:
    engine = retainer("mireille", betrayal_risk=True, loyalty=10)
    put(engine, "sheet.competence", balance.COUP_COMPETENCE)
    engine.turn()
    assert get(engine.state, "beats.coup") is True
    assert any("turns on Ars" in text for text in engine.instructions)


def test_a_loyal_retainer_never_betrays() -> None:
    engine = retainer("ritsu", betrayal_risk=True, loyalty=balance.BETRAYAL_LOYALTY)
    engine.turn()
    assert get(engine.state, attr("ritsu", "is_recruited")) is True
