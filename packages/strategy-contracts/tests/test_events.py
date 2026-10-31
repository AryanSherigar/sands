from uuid import uuid4

import pytest
from pydantic import ValidationError
from strategy_contracts.conditions import (
    SUBJECT_PLACEHOLDER,
    Comparison,
    ConditionMetric,
    ConditionOperator,
    ConditionScope,
)
from strategy_contracts.event_catalog import (
    BUILTIN_EVENT_IDS,
    BUILTIN_EVENTS,
    DISASTER_EVENT_IDS,
    DISASTER_EVENTS,
    effective_events,
)
from strategy_contracts.events import (
    EventDefinition,
    EventNarrativeBriefing,
    EventNarrativeClaim,
    EventNarrativeCompleteInput,
    EventNarrativeFailInput,
    EventNarrativePayload,
    EventNarrativeView,
)
from strategy_contracts.scenario import StrategyScenario

FIRST_UNREST_TIER = 40
SECOND_UNREST_TIER = 60


def _unrest(value: int, subject_id: str | None = SUBJECT_PLACEHOLDER) -> Comparison:
    return Comparison(
        metric=ConditionMetric.REGION_UNREST,
        subject_id=subject_id,
        operator=ConditionOperator.GTE,
        value=value,
    )


def _event(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "custom_event",
        "name": "Custom",
        "subject_kind": "region",
        "cause_key": "custom_event",
        "tiers": [
            {"level": 1, "trigger": _unrest(FIRST_UNREST_TIER).model_dump()},
            {"level": 2, "trigger": _unrest(SECOND_UNREST_TIER).model_dump()},
        ],
        "choices": [
            {"id": "one", "label_hint": "one", "effects": []},
            {"id": "two", "label_hint": "two", "effects": []},
        ],
        "neglect_effects": [{"kind": "region_unrest", "amount": 5}],
    }
    return base | overrides


def test_builtin_events_validate_and_have_unique_ids() -> None:
    assert len(BUILTIN_EVENTS) == 4
    assert len(BUILTIN_EVENT_IDS) == 6
    assert [event.id for event in BUILTIN_EVENTS] == sorted(
        BUILTIN_EVENT_IDS - DISASTER_EVENT_IDS
    )


def test_builtin_events_cover_each_subject_kind() -> None:
    kinds = {event.subject_kind for event in BUILTIN_EVENTS}
    assert kinds == {
        ConditionScope.REGION,
        ConditionScope.GOVERNOR,
        ConditionScope.ARMY,
        ConditionScope.FACTION,
    }


def test_custom_event_round_trips() -> None:
    event = EventDefinition.model_validate(_event())
    assert EventDefinition.model_validate(event.model_dump()) == event


def test_tier_levels_must_strictly_increase() -> None:
    tiers = [
        {"level": 2, "trigger": _unrest(FIRST_UNREST_TIER).model_dump()},
        {"level": 1, "trigger": _unrest(SECOND_UNREST_TIER).model_dump()},
    ]
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(_event(tiers=tiers))


def test_choice_ids_must_be_unique() -> None:
    choices = [
        {"id": "same", "label_hint": "a", "effects": []},
        {"id": "same", "label_hint": "b", "effects": []},
    ]
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(_event(choices=choices))


def test_region_metric_needs_the_subject_placeholder() -> None:
    tiers = [{"level": 1, "trigger": _unrest(40, "brennmoor").model_dump()}]
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(_event(tiers=tiers))


def test_metric_out_of_scope_for_the_subject_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(_event(subject_kind="faction"))


def test_event_needs_a_neglect_outcome() -> None:
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(_event(neglect_effects=[]))


def test_order_cost_is_bounded() -> None:
    choices = [
        {"id": "one", "label_hint": "a", "effects": [], "order_cost": 0},
        {"id": "two", "label_hint": "b", "effects": []},
    ]
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(_event(choices=choices))


def test_threshold_is_required_only_for_the_regions_in_unrest_metric() -> None:
    with pytest.raises(ValidationError):
        Comparison(
            metric=ConditionMetric.REGIONS_WITH_UNREST_AT_LEAST,
            operator=ConditionOperator.GTE,
            value=2,
        )
    with pytest.raises(ValidationError):
        Comparison(
            metric=ConditionMetric.TREASURY,
            operator=ConditionOperator.GTE,
            value=2,
            threshold=60,
        )


def test_custom_event_replaces_a_builtin_with_the_same_id() -> None:
    custom = EventDefinition.model_validate(_event(id="tax_grievance"))
    events = effective_events([custom], [])
    assert len(events) == len(BUILTIN_EVENTS)
    assert next(e for e in events if e.id == "tax_grievance") == custom


def test_disabled_builtins_are_dropped_and_order_is_stable() -> None:
    events = effective_events([], ["tax_grievance"])
    assert "tax_grievance" not in {event.id for event in events}
    assert [event.id for event in events] == sorted(event.id for event in events)


def test_scenario_accepts_disabled_builtin_ids() -> None:
    scenario = StrategyScenario(disabled_builtin_event_ids=["tax_grievance"])
    assert scenario.disabled_builtin_event_ids == ["tax_grievance"]


@pytest.mark.parametrize("kind", ["opinion", "add_memory", "start_diplomatic_play"])
def test_effect_kinds_the_engine_cannot_apply_are_rejected(kind: str) -> None:
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(
            _event(neglect_effects=[{"kind": kind, "amount": 1}])
        )


def test_ruler_dies_is_a_supported_effect() -> None:
    from strategy_contracts.events import EffectKind, EffectSpec

    assert EffectSpec(kind=EffectKind.RULER_DIES).amount == 0


def _faction_event(**overrides: object) -> dict[str, object]:
    trigger = Comparison(
        metric=ConditionMetric.TREASURY, operator=ConditionOperator.LT, value=100
    )
    return _event(
        subject_kind="faction",
        tiers=[{"level": 1, "trigger": trigger.model_dump()}],
        neglect_effects=[{"kind": "gold", "amount": -5}],
        **overrides,
    )


def test_new_event_fields_default_to_todays_behaviour() -> None:
    for event in BUILTIN_EVENTS:
        assert event.chance_percent == 100
        assert event.applies_to_npcs is False


def test_chance_percent_is_bounded() -> None:
    for bad_value in (101, -1):
        with pytest.raises(ValidationError):
            EventDefinition.model_validate(_event(chance_percent=bad_value))


def test_applies_to_npcs_needs_a_faction_subject() -> None:
    with pytest.raises(ValidationError):
        EventDefinition.model_validate(_event(applies_to_npcs=True))
    event = EventDefinition.model_validate(_faction_event(applies_to_npcs=True))
    assert event.applies_to_npcs is True


def test_disaster_templates_are_sorted_faction_events_open_to_npcs() -> None:
    assert [event.id for event in DISASTER_EVENTS] == ["bad_harvest", "plague"]
    assert set(DISASTER_EVENT_IDS) == {"bad_harvest", "plague"}
    for event in DISASTER_EVENTS:
        assert event.subject_kind is ConditionScope.FACTION
        assert event.applies_to_npcs is True
        assert 0 < event.chance_percent < 100


def test_disaster_ids_are_valid_builtin_ids_for_disabling() -> None:
    from strategy_contracts.examples import load_three_crowns
    from strategy_contracts.publish_checks import check_publishable

    assert DISASTER_EVENT_IDS <= BUILTIN_EVENT_IDS
    scenario = load_three_crowns().model_copy(
        update={"disabled_builtin_event_ids": ["plague"]}
    )
    assert check_publishable(scenario).blocking == []


def test_effective_events_hides_disasters_until_asked() -> None:
    assert len(effective_events([], [])) == 4
    with_disasters = effective_events([], [], has_disasters=True)
    assert len(with_disasters) == 6
    assert [event.id for event in with_disasters] == sorted(
        event.id for event in with_disasters
    )
    disabled = effective_events([], ["plague"], has_disasters=True)
    assert "plague" not in {event.id for event in disabled}
    custom = EventDefinition.model_validate(_event(id="plague"))
    replaced = effective_events([custom], [], has_disasters=True)
    assert next(event for event in replaced if event.id == "plague") == custom


def test_each_disaster_has_a_costly_first_choice_and_neglect_effects() -> None:
    for event in DISASTER_EVENTS:
        assert 2 <= len(event.choices) <= 3
        first = event.choices[0]
        assert any(
            effect.kind.value == "gold" and effect.amount < 0
            for effect in first.effects
        )
        assert event.neglect_effects


def test_each_disaster_has_three_ascending_tiers_and_cause_metrics() -> None:
    for event in DISASTER_EVENTS:
        assert [tier.level for tier in event.tiers] == [1, 2, 3]
        assert ConditionMetric.MONTH in event.cause_metrics
        assert event.cause_metrics


def test_event_narrative_models_validate() -> None:
    payload = EventNarrativePayload(
        body_prose="The town bailiffs arrived with grim faces.",
        cause_quote="We have no grain left to give.",
        character_name="Alderman Morvath",
        character_title="Guild Representative",
        disposition="Defiant",
    )
    briefing = EventNarrativeBriefing(
        playthrough_id=uuid4(),
        event_id="pending_event_1",
        template_id="tax_grievance",
        template_name="Tax grievance",
        subject_name="Dunmere Vale",
        region_id="reg_dunmere",
        tier=2,
        cause_description="unrest is 45",
        ruler_name="Aldric Vane",
        ruler_traits=["stern", "greedy"],
        season_year="Spring 1001",
        choices=[{"choice_id": "grant_remission", "label": "Grant tax relief"}],
    )
    lease_token = uuid4()
    claim = EventNarrativeClaim(lease_token=lease_token, briefing=briefing)
    complete = EventNarrativeCompleteInput(
        lease_token=lease_token,
        narration=payload,
    )
    fail_input = EventNarrativeFailInput(
        lease_token=lease_token,
        error_code="provider_timeout",
    )
    view = EventNarrativeView(
        event_id="pending_event_1",
        status="completed",
        narration=payload,
    )
    assert claim.lease_token == lease_token
    assert complete.narration.character_name == "Alderman Morvath"
    assert fail_input.error_code == "provider_timeout"
    assert view.status == "completed"
    assert briefing.event_id == "pending_event_1"
