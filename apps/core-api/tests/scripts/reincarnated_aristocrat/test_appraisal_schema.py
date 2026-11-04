from app.models.content_tags import validate_content_tags
from app.services.display_hints import validate_display_hints
from app.services.narrator_rules import (
    intent_marker_group_from_rules,
    narration_limit_from_rules,
)
from app.services.schema_field_validation import validate_schema_fields
from app.services.state_visibility import visible_schema, visible_state
from app.tools.registry import close_over_requires
from scripts.reincarnated_aristocrat import builder, characters, prose, schema
from scripts.reincarnated_aristocrat.characters import CHARACTER_SLUGS
from scripts.seeding.fields import flatten_schema


def _built() -> builder.AppraisalScenario:
    return builder.build()


def test_schema_passes_the_core_api_validators() -> None:
    state_schema = schema.build_state_schema()
    validate_schema_fields(state_schema, builder.ENABLED_TOOLS)
    validate_display_hints(state_schema, builder.ENABLED_TOOLS)


def test_enabled_tools_are_closed_over_requirements() -> None:
    closed, added = close_over_requires(builder.ENABLED_TOOLS)
    assert closed == builder.ENABLED_TOOLS
    assert added == []


def test_content_tags_are_in_the_vocabulary() -> None:
    tags = _built().scenario["content_tags"]
    assert validate_content_tags(tags) == tags  # type: ignore[arg-type]
    assert _built().scenario["content_tag"] == "teen"


def test_the_five_house_stats_are_visible_meters() -> None:
    fields = flatten_schema(schema.build_state_schema())
    for key, label, maximum, _ in schema.HOUSE_STATS:
        assert fields[key]["display"]["kind"] == "meter"  # type: ignore[index]
        assert fields[key]["label"] == label
        assert fields[key]["max"] == maximum


def test_the_hidden_sheet_clock_and_intents_never_reach_the_client() -> None:
    state_schema = schema.build_state_schema()
    exposed = visible_schema(state_schema)
    assert set(exposed) == {"player", *(key for key, *_ in schema.HOUSE_STATS)}
    initial = {
        "sheet": {"fear": 90},
        "time": {"clock_days": 5},
        "intent": {"train_who": "ritsu"},
        "funds": 60,
    }
    assert visible_state(initial, state_schema) == {"funds": 60}


def test_competence_is_derived_so_the_narrator_cannot_write_it() -> None:
    fields = flatten_schema(schema.build_state_schema())
    assert fields["sheet.competence"]["derived"] is True


def test_every_intent_flag_starts_unset() -> None:
    fields = flatten_schema(schema.build_state_schema())
    intents = {
        path: item for path, item in fields.items() if path.startswith("intent.")
    }
    assert len(intents) == 6
    assert all(item["initial"] == "" for item in intents.values())
    assert set(fields["intent.appraise_target"]["options"]) == {"", *CHARACTER_SLUGS}  # type: ignore[arg-type]


def test_the_scenario_is_a_master_mode_draft_without_setup_choices() -> None:
    columns = _built().scenario
    assert columns["mode"] == "master"
    assert columns["setup_schema"] == []
    assert columns["action_chips"] == builder.ACTION_CHIPS
    assert len(builder.ACTION_CHIPS) == 4
    assert len(str(columns["logline"])) <= 150


def test_entities_total_ten_characters_and_28_locations() -> None:
    kinds = [seed.payload.entity_type for seed in _built().entities]
    assert kinds.count("character") == 10
    assert kinds.count("location") == 28
    assert len({seed.slug for seed in _built().entities}) == 38


def test_scenario_sets_its_own_narration_output_limit() -> None:
    rules = builder.scenario_columns()["rules"]

    assert narration_limit_from_rules(rules) == prose.NARRATION_MAX_OUTPUT_TOKENS
    assert prose.NARRATION_MAX_OUTPUT_TOKENS > 600


def test_persona_asks_for_longer_multi_character_scenes() -> None:
    assert prose.PERSONA_LENGTH in prose.PERSONA
    assert "several characters" in prose.PERSONA_LENGTH


def test_scenario_opts_in_to_the_intent_marker_for_a_real_schema_group() -> None:
    columns = builder.scenario_columns()

    group = intent_marker_group_from_rules(columns["rules"], columns["state_schema"])

    assert group == schema.INTENT_GROUP == "intent"


def test_persona_asks_for_the_marker_not_a_tool_call() -> None:
    assert "[INTENT:" in prose.PERSONA_INTENT
    assert "set_field" not in prose.PERSONA


def test_persona_marker_keys_are_real_intent_fields() -> None:
    intent_fields = schema.build_state_schema()[schema.INTENT_GROUP]["fields"]

    for key in (
        "recruit_target",
        "train_who",
        "train_stat",
        "adopt_policy",
        "time_cost",
    ):
        assert key in intent_fields
        assert f"{key}=" in prose.PERSONA_INTENT


def test_persona_requires_both_training_keys_and_excludes_ars() -> None:
    assert "both keys" in prose.PERSONA_INTENT
    assert "Ars himself cannot be trained" in prose.PERSONA_INTENT


def test_persona_roster_carries_every_character_age_rule_and_aptitudes() -> None:
    for spec in characters.CHARACTERS:
        assert spec.name in prose.PERSONA_ROSTER
        assert characters.age_note(spec) in prose.PERSONA_ROSTER
        assert characters.aptitude_line(spec) in prose.PERSONA_ROSTER
    assert prose.PERSONA_ROSTER in prose.PERSONA


def test_every_character_has_pronouns_in_the_roster() -> None:
    for spec in characters.CHARACTERS:
        assert characters.PRONOUNS[spec.slug] in prose.PERSONA_ROSTER


def test_age_has_a_hud_meter() -> None:
    age = schema.build_state_schema()["player"]["fields"]["age"]

    assert age["display"]["kind"] == "meter"
