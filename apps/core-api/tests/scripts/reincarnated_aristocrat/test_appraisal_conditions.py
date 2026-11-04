import pytest
from engine_sim import Engine, apply, get, new_engine
from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.ids import entity_id


def attr(slug: str, name: str) -> str:
    return f"{entity_id(slug)}.{name}"


def put(engine: Engine, path: str, value: object) -> None:
    engine.state = apply(engine.state, path, "set", value)


def test_every_turn_advances_the_counter_and_the_clock() -> None:
    engine = new_engine()
    engine.run(10)
    assert get(engine.state, "time.turns") == 10
    assert get(engine.state, "time.clock_days") == 10 * balance.DAYS_PER_TURN


def test_a_time_cost_adds_days_once_and_clears_its_flag() -> None:
    engine = new_engine()
    put(engine, "intent.time_cost", "long")
    engine.turn()
    expected = balance.DAYS_PER_TURN + balance.TIME_COST_DAYS["long"]
    assert get(engine.state, "time.clock_days") == expected
    assert get(engine.state, "intent.time_cost") == ""


def test_ars_ages_up_on_his_birthdays() -> None:
    engine = new_engine()
    put(engine, "time.clock_days", balance.DAYS_PER_YEAR - balance.DAYS_PER_TURN)
    assert get(engine.state, "player.age") == 6
    engine.turn()
    assert get(engine.state, "player.age") == 7
    assert any("turned 7" in text for text in engine.instructions)


def test_the_canon_beats_arrive_in_order_and_only_once() -> None:
    engine = new_engine()
    seen: list[str] = []
    for _ in range(160):
        seen += [text for text in engine.turn() if "Raven" in text]
    beats = {
        name: get(engine.state, f"beats.{name}")
        for name in (
            "engaged",
            "illness_begun",
            "raven_dead",
            "couran_called",
            "fahm_findable",
            "mireille_findable",
        )
    }
    assert all(beats.values()), beats
    assert sum("Raven Louvent dies" in text for text in seen) == 1
    assert sum("Raven's health begins to fail" in text for text in seen) == 1


def test_raven_cannot_die_before_his_illness_has_begun() -> None:
    engine = new_engine()
    put(engine, "time.clock_days", balance.DEATH_DAY + 1)
    engine.turn()
    assert get(engine.state, "beats.illness_begun") is True
    assert get(engine.state, "beats.raven_dead") is True


def test_fahm_and_mireille_only_become_findable_after_raven() -> None:
    engine = new_engine()
    engine.run(60)
    assert get(engine.state, "beats.fahm_findable") is False
    assert get(engine.state, "beats.mireille_findable") is False


def test_appraising_someone_marks_them_and_clears_the_flag() -> None:
    engine = new_engine()
    put(engine, "intent.appraise_target", "ritsu")
    engine.turn()
    assert get(engine.state, attr("ritsu", "is_appraised")) is True
    assert get(engine.state, attr("rosell", "is_appraised")) is False
    assert get(engine.state, "intent.appraise_target") == ""


def test_recruiting_adds_a_retainer_with_loyalty_army_and_standing() -> None:
    engine = new_engine()
    put(engine, "intent.recruit_target", "ritsu")
    engine.turn()
    assert get(engine.state, attr("ritsu", "is_recruited")) is True
    assert get(engine.state, attr("ritsu", "loyalty")) == balance.RECRUIT_START_LOYALTY
    assert get(engine.state, "time.recruits") == 1
    assert get(engine.state, "army_strength") == 5 + balance.ARMY_VALUE["ritsu"]
    assert get(engine.state, "standing") == 10 + balance.RECRUIT_STANDING


@pytest.mark.parametrize("slug", ["lysia", "fahm", "mireille"])
def test_late_candidates_cannot_be_recruited_before_their_beat(slug: str) -> None:
    engine = new_engine()
    put(engine, "intent.recruit_target", slug)
    engine.turn()
    assert get(engine.state, attr(slug, "is_recruited")) is False
    assert get(engine.state, "intent.recruit_target") == ""
    assert any("cannot happen now" in text for text in engine.instructions)


def test_a_policy_costs_the_house_and_applies_its_effects() -> None:
    engine = new_engine()
    put(engine, "intent.adopt_policy", "strict_law")
    engine.turn()
    spec = balance.POLICY_SPECS["strict_law"]
    assert get(engine.state, "policies.strict_law") is True
    assert get(engine.state, "funds") == 60 - spec.funds
    assert get(engine.state, "control") == 40 + 12
    assert get(engine.state, "sheet.fear") == 10 + 10
    assert get(engine.state, "sheet.goodwill") == 50 - 8


def test_an_unaffordable_or_repeated_policy_changes_nothing() -> None:
    engine = new_engine()
    put(engine, "funds", 5)
    put(engine, "intent.adopt_policy", "farmland_development")
    engine.turn()
    assert get(engine.state, "policies.farmland_development") is False
    assert get(engine.state, "funds") == 5
    assert get(engine.state, "intent.adopt_policy") == ""


def test_the_first_month_pays_income_and_moves_the_due_date() -> None:
    engine = new_engine()
    engine.run(2)
    assert get(engine.state, "time.next_income_day") == 2 * balance.MONTH_DAYS
    assert get(engine.state, "funds") == 60 + balance.BASE_INCOME
    assert get(engine.state, "resources") == 40 + balance.BASE_RESOURCES


def test_a_long_journey_is_processed_one_month_per_turn() -> None:
    engine = new_engine()
    put(engine, "time.clock_days", 200)
    engine.turn()
    assert get(engine.state, "time.next_income_day") == 2 * balance.MONTH_DAYS
    engine.run(10)
    behind = get(engine.state, "time.clock_days") - get(
        engine.state, "time.next_income_day"
    )
    assert behind < balance.MONTH_DAYS


def test_retainers_cost_upkeep_each_month() -> None:
    engine = new_engine()
    put(engine, attr("ritsu", "is_recruited"), True)
    put(engine, "time.clock_days", 15)
    engine.turn()
    gain = balance.BASE_INCOME - balance.UPKEEP_PER_RETAINER
    assert get(engine.state, "funds") == 60 + gain


def test_a_standing_policy_changes_the_monthly_income() -> None:
    engine = new_engine()
    put(engine, "policies.tax_relief", True)
    put(engine, "time.clock_days", 15)
    engine.turn()
    assert get(engine.state, "funds") == 60 + balance.BASE_INCOME - 5


def test_training_resets_each_month() -> None:
    engine = new_engine()
    put(engine, attr("ritsu", "has_trained"), True)
    put(engine, "time.clock_days", 15)
    engine.turn()
    assert get(engine.state, attr("ritsu", "has_trained")) is False


def test_a_month_that_starts_in_debt_is_counted_and_then_cleared() -> None:
    engine = new_engine()
    put(engine, "funds", 3)
    put(engine, "time.clock_days", 15)
    engine.turn()
    assert get(engine.state, "time.debt_months") == 1
    put(engine, "funds", 200)
    put(engine, "time.clock_days", 45)
    engine.turn()
    assert get(engine.state, "time.debt_months") == 0


def test_a_quiet_run_only_ever_hits_the_ceilings_of_a_growing_house() -> None:
    engine = new_engine()
    engine.run(200)
    paths = {item.split(": ")[1] for item in engine.rejected}
    assert paths <= {"funds", "resources", "sheet.competence"}
    assert get(engine.state, "time.debt_months") == 0
