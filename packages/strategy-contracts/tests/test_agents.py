from uuid import uuid4

import pytest
from pydantic import ValidationError
from strategy_contracts.agents import (
    AgentTrait,
    AgentTuning,
    AgentView,
    DispatchBriefing,
)
from strategy_contracts.pressure import PressureBand, RumorTopic
from strategy_contracts.scenario import Tuning


def test_agent_tuning_defaults_are_disabled_with_chosen_values() -> None:
    tuning = AgentTuning()

    assert tuning.is_enabled is False
    assert tuning.loyalty_min == 20
    assert tuning.loyalty_max == 80
    assert tuning.pious_loyalty_bonus == 15
    assert tuning.honest_wrong_reduction_percent == 15
    assert tuning.incompetent_wrong_bonus_percent == 20
    assert tuning.deceitful_calm_steps == 1
    assert tuning.bribed_calm_steps == 2
    assert tuning.bribe_base_price == 40
    assert tuning.bribe_price_per_loyalty == 2
    assert tuning.incompetent_bribe_discount_percent == 30
    assert tuning.bribe_score_bonus == 6


def test_scenario_tuning_exposes_agents() -> None:
    assert Tuning().agents.is_enabled is False


def test_dispatch_briefing_forbids_extra_fields() -> None:
    fields: dict[str, object] = {
        "rumor_id": "rumor_1",
        "playthrough_id": uuid4(),
        "turn": 3,
        "agent": AgentView(name="Odo", traits=[AgentTrait.HONEST]),
        "about_faction_id": "valdren",
        "topic": RumorTopic.WILL,
        "reported_band": PressureBand.HIGH,
    }
    DispatchBriefing(**fields)

    for forbidden in ("true_band", "bribed_by", "is_hint_wrong"):
        with pytest.raises(ValidationError):
            DispatchBriefing(**fields, **{forbidden: "x"})
