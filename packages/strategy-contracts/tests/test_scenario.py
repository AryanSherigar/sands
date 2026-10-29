import pytest
from pydantic import ValidationError
from strategy_contracts.conditions import Comparison, ConditionMetric, ConditionOperator
from strategy_contracts.enums import OrderKind
from strategy_contracts.events import EventChoice, EventDefinition
from strategy_contracts.scenario import (
    CommanderSetup,
    FactionSetup,
    PlayerRulerCustomization,
    StrategyScenario,
    Tuning,
)

TRIGGER = Comparison(
    metric=ConditionMetric.TURN, operator=ConditionOperator.GTE, value=1
)


def _choice(choice_id: str) -> EventChoice:
    return EventChoice(id=choice_id, label_hint="hint", effects=[])


def _event(choice_count: int) -> dict[str, object]:
    return {
        "id": "border_incident",
        "name": "Border incident",
        "subject_kind": "faction",
        "cause_key": "border_incident",
        "tiers": [{"level": 1, "trigger": TRIGGER.model_dump()}],
        "neglect_effects": [{"kind": "stability", "amount": -1}],
        "choices": [
            _choice(f"choice_{index}").model_dump() for index in range(choice_count)
        ],
    }


def test_empty_draft_parses() -> None:
    assert StrategyScenario().factions == []


def test_json_round_trip_keeps_equality() -> None:
    scenario = StrategyScenario()
    restored = StrategyScenario.model_validate_json(scenario.model_dump_json())
    assert restored == scenario


def test_extra_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        StrategyScenario.model_validate({"surprise": 1})


def test_negative_treasury_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FactionSetup(id="house_a", name="A", color="#aabbcc", treasury=-1)


def test_stability_above_100_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FactionSetup(id="house_a", name="A", color="#aabbcc", stability=101)


def test_bad_color_is_rejected() -> None:
    with pytest.raises(ValidationError):
        FactionSetup(id="house_a", name="A", color="red")


def test_default_cost_table_covers_every_order_kind() -> None:
    assert set(Tuning().order_costs) == set(OrderKind)
    assert Tuning().orders_per_turn == 6


def test_default_scenario_has_visibility_tuning() -> None:
    assert StrategyScenario().tuning.visibility.ruleset_version == 1


@pytest.mark.parametrize("choice_count", [1, 5])
def test_event_choice_count_is_bounded(choice_count: int) -> None:
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(_event(choice_count))


def test_event_with_two_choices_is_accepted() -> None:
    assert len(EventDefinition.model_validate(_event(2)).choices) == 2


def test_commander_with_three_traits_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CommanderSetup(
            id="cmd_a",
            name="A",
            faction_id="house_a",
            trait_ids=["cruel", "proud", "wrathful"],
        )


def test_dangling_reference_in_a_draft_still_parses() -> None:
    faction = FactionSetup(
        id="house_a", name="A", color="#aabbcc", capital_region_id="nowhere"
    )
    assert (
        StrategyScenario(factions=[faction]).factions[0].capital_region_id == "nowhere"
    )


def test_player_ruler_customization_valid() -> None:
    ruler = PlayerRulerCustomization(
        name="King Alden IV",
        epithet="Sovereign of the Marches",
        portrait_url="https://example.com/alden.png",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
        backstory="A resolute monarch.",
    )
    assert ruler.name == "King Alden IV"
    assert ruler.epithet == "Sovereign of the Marches"
    assert ruler.portrait_url == "https://example.com/alden.png"
    assert len(ruler.trait_ids) == 2
    assert len(ruler.ambition_ids) == 1
    assert ruler.backstory == "A resolute monarch."


def test_player_ruler_customization_trait_bounds() -> None:
    with pytest.raises(ValidationError):
        PlayerRulerCustomization(
            name="Alden",
            trait_ids=["honorable"],  # Too few traits (min 2)
            ambition_ids=["ambition_peace"],
        )
    with pytest.raises(ValidationError):
        PlayerRulerCustomization(
            name="Alden",
            trait_ids=[
                "honorable",
                "cautious",
                "proud",
                "wrathful",
            ],  # Too many (max 3)
            ambition_ids=["ambition_peace"],
        )


def test_player_ruler_customization_ambition_bounds() -> None:
    with pytest.raises(ValidationError):
        PlayerRulerCustomization(
            name="Alden",
            trait_ids=["honorable", "cautious"],
            ambition_ids=[],  # Too few ambitions (min 1)
        )
    with pytest.raises(ValidationError):
        PlayerRulerCustomization(
            name="Alden",
            trait_ids=["honorable", "cautious"],
            ambition_ids=["ambition_1", "ambition_2", "ambition_3"],  # Too many (max 2)
        )
