from strategy_contracts.examples import load_three_crowns
from strategy_contracts.overtures import OvertureKind, OvertureTuning
from strategy_contracts.scenario import SystemToggles, Tuning


def test_defaults_validate() -> None:
    assert OvertureTuning().cooldown_turns == 4


def test_overture_kinds_are_the_seven_named() -> None:
    assert {kind.value for kind in OvertureKind} == {
        "peace_offer",
        "demand",
        "call_for_talks",
        "heir_renewal",
        "ransom_demand",
        "ransom_counter",
        "oath_offer",
    }


def test_tuning_roundtrips_in_three_crowns_example() -> None:
    scenario = load_three_crowns()
    assert scenario.tuning.overtures == OvertureTuning()
    assert Tuning().overtures == OvertureTuning()


def test_toggle_defaults_on() -> None:
    assert SystemToggles().is_overtures_enabled is True
