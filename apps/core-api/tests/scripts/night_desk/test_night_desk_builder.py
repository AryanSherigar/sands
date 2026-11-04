"""The built scenario: shape, tools, tiers, persona, schema and display hints."""

import pytest
from app.tools.registry import close_over_requires
from scripts.night_desk import prose, schema
from scripts.night_desk.builder import ENABLED_TOOLS, build
from scripts.night_desk.validation import validate

try:
    from mini_eval import evaluate
except ImportError:  # pytest rootdir-relative import fallback
    from tests.scripts.night_desk.mini_eval import evaluate

HIDDEN_ROOTS = (
    "seed",
    "fragments",
    "flags",
    "events",
    "visited",
    "dwell",
    "check",
    "visit",
    "count",
    "cabin",
    "violations_count",
)
TIERS = ("Clear", "Frayed", "Paranoid", "Unravelling")


@pytest.fixture(scope="module")
def built():
    return build()


def test_scenario_validates_clean(built):
    assert validate(built) == []


def test_all_five_tools_are_enabled_and_closed_over_requires(built):
    assert built.scenario["enabled_tools"] == ENABLED_TOOLS
    assert close_over_requires(ENABLED_TOOLS)[1] == []


def test_the_authored_volume(built):
    assert 60 <= len(built.conditions) <= 110
    assert len(built.rule_checks) == 10
    assert len(built.sheet_rules) == 8
    assert len(built.minigames) == 1
    assert len(built.end_conditions) == 4
    assert len(built.entities) == 19
    assert len(built.facts) == 3


def test_removed_constructs_are_gone(built):
    labels = [condition.label for condition in built.conditions]
    assert not any("[" in label for label in labels)
    assert all(condition.state_mutation is None for condition in built.conditions)
    text = str([c.narrator_instruction for c in built.conditions])
    assert "Cage" not in text and "recall" not in text.lower()


def test_persona_opening_duties_and_chips(built):
    scenario = built.scenario
    assert scenario["narrator_persona"] == prose.PERSONA
    assert scenario["opening_scene"] == prose.OPENING_SCENE
    assert scenario["world_data"]["duties"] == list(prose.DUTIES)
    assert scenario["world_data"]["escalation_reply"] == "Acknowledged."
    assert "the new clerk" in scenario["world_data"]["openingPrompt"]
    assert scenario["estimated_playtime"] == "20m"
    assert scenario["action_chips"] == [
        "Check the Log",
        "File a folder",
        "Look around",
        "Wait",
    ]


@pytest.mark.parametrize("sanity", range(-100, 101))
def test_exactly_one_sanity_tier_applies(built, sanity):
    tiers = [c for c in built.conditions if c.label.startswith("T1")]
    active = [
        c.label for c in tiers if evaluate(c.condition_expression, {"sanity": sanity})
    ]
    assert len(active) == 1


@pytest.mark.parametrize(
    ("sanity", "expected_tier"),
    [
        (100, "Clear"),
        (75, "Clear"),
        (74, "Frayed"),
        (50, "Frayed"),
        (49, "Paranoid"),
        (25, "Paranoid"),
        (24, "Unravelling"),
        (0, "Unravelling"),
        (-8, "Unravelling"),
    ],
)
def test_tier_boundaries(built, sanity, expected_tier):
    tiers = [c for c in built.conditions if c.label.startswith("T1")]
    active = [
        c.label for c in tiers if evaluate(c.condition_expression, {"sanity": sanity})
    ]
    assert active == [f"T1{TIERS.index(expected_tier) + 1} Sanity tier {expected_tier}"]


def test_secrets_are_hidden_and_the_hud_fields_are_not(built):
    state_schema = built.scenario["state_schema"]
    assert all(state_schema[root].get("hidden") is True for root in HIDDEN_ROOTS)
    for visible in ("shift_minutes", "sanity", "tension_tier", "player"):
        assert "hidden" not in state_schema[visible]


def test_the_seed_is_drawn_per_playthrough(built):
    seed = built.scenario["state_schema"]["seed"]["fields"]["false_rule"]
    assert seed["initial_random"] == ["r4", "r6"]
    assert set(seed["initial_random"]) <= set(seed["options"])


def test_initial_state_is_valid_for_the_shift_clock():
    fields = schema.flatten_schema(schema.build_state_schema())
    assert fields["shift_minutes"]["initial"] == 0
    assert fields["sanity"]["initial"] == 85
    assert fields["sanity"]["min"] < 0, "sanity must be able to cross zero"


def test_display_hints_describe_a_clock_a_meter_and_a_tier(built):
    state_schema = built.scenario["state_schema"]
    assert state_schema["shift_minutes"]["display"]["kind"] == "clock"
    assert state_schema["sanity"]["display"]["kind"] == "meter"
    assert state_schema["tension_tier"]["display"]["kind"] == "tier"
    assert "intrusive_thoughts" not in state_schema["sanity"]["display"]["effects"]


def test_every_condition_with_an_image_or_effect_validates(built):
    with_metadata = [
        c
        for c in built.conditions
        if c.metadata.get("client_effect") or c.metadata.get("authored_image_url")
    ]
    assert len(with_metadata) == 4
