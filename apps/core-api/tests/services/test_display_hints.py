"""Display-hint validation, tool gating and snapshot stripping (tool `status_hud`)."""

import copy
import uuid

import pytest
from app.config import settings
from app.exceptions.display_hint_exceptions import DisplayHintValidationError
from app.exceptions.tool_exceptions import ToolNotEnabledError
from app.models.playthrough import PlaythroughCreate
from app.models.scenario import ScenarioCreate, ScenarioUpdate
from app.models.tools import ToolsUpdate
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.display_hints import (
    strip_display_hints,
    tier_track_keys,
    validate_display_hints,
)
from app.services.scenario_service import ScenarioService
from app.services.tier_music import resolve_tier_track_urls
from app.services.tool_service import ToolService
from sqlalchemy.ext.asyncio import AsyncSession
from tests.services.test_tool_snapshot import _make_service

CLOCK = {
    "type": "number",
    "initial": 0,
    "display": {
        "kind": "clock",
        "label": "Shift",
        "start": "23:00",
        "format": "12h",
        "glitch": {"source": "sanity", "below": 25, "chance": 0.02},
    },
}
METER = {
    "type": "number",
    "min": -100,
    "max": 100,
    "initial": 85,
    "display": {
        "kind": "meter",
        "label": "Sanity",
        "clamp_min": 0,
        "clamp_max": 100,
        "tiers": [
            {"name": "clear", "min": 75},
            {"name": "frayed", "min": 50},
            {"name": "unraveling"},
        ],
        "effects": {"moderate_below": 50, "critical_below": 25},
    },
}
TIER = {
    "type": "enum",
    "options": ["uneasy", "tense", "dread"],
    "initial": "uneasy",
    "display": {
        "kind": "tier",
        "label": "Tension",
        "mood_map": {"uneasy": "mystery", "tense": "tension", "dread": "combat"},
        "track_map": {
            "uneasy": "night-desk-music/uneasy.mp3",
            "tense": "night-desk-music/tense.mp3",
            "dread": "night-desk-music/dread.mp3",
        },
    },
}
HUD_ON = ["status_hud"]


def _schema(**fields) -> dict:
    return copy.deepcopy(fields)


def _valid() -> dict:
    return _schema(shift_minutes=CLOCK, sanity=METER, tension_tier=TIER)


def test_a_full_valid_hud_passes() -> None:
    validate_display_hints(_valid(), HUD_ON)


def test_a_schema_without_hints_needs_no_tool() -> None:
    validate_display_hints({"gold": {"type": "number"}}, [])


def test_hints_are_rejected_naming_the_tool_when_it_is_off() -> None:
    with pytest.raises(ToolNotEnabledError) as raised:
        validate_display_hints(_valid(), [])

    assert raised.value.tool_key == "status_hud"


def test_hints_inside_an_object_are_found() -> None:
    schema = {"player": {"type": "object", "fields": {"sanity": copy.deepcopy(METER)}}}

    with pytest.raises(ToolNotEnabledError):
        validate_display_hints(schema, [])


@pytest.mark.parametrize("kind", ["clock", "meter"])
def test_clock_and_meter_need_a_number_field(kind: str) -> None:
    field = copy.deepcopy(CLOCK if kind == "clock" else METER)
    field["type"] = "string"

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"x": field, "sanity": METER}, HUD_ON)


def test_tier_needs_an_enum_field() -> None:
    field = copy.deepcopy(TIER)
    field["type"] = "number"

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"tension": field}, HUD_ON)


def test_unknown_kind_is_rejected() -> None:
    field = {"type": "number", "display": {"kind": "gauge", "label": "x"}}

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"x": field}, HUD_ON)


def test_two_clocks_are_rejected() -> None:
    with pytest.raises(DisplayHintValidationError):
        validate_display_hints(_schema(a=CLOCK, b=CLOCK, sanity=METER), HUD_ON)


def test_two_tiers_are_rejected() -> None:
    with pytest.raises(DisplayHintValidationError):
        validate_display_hints(_schema(a=TIER, b=TIER), HUD_ON)


def _meter_without_effects() -> dict:
    meter = copy.deepcopy(METER)
    del meter["display"]["effects"]
    return meter


def test_any_number_of_meters_is_fine() -> None:
    validate_display_hints(
        _schema(sanity=METER, battery=_meter_without_effects()), HUD_ON
    )


def test_only_one_meter_may_define_effects() -> None:
    with pytest.raises(DisplayHintValidationError, match="only one meter"):
        validate_display_hints(_schema(sanity=METER, battery=METER), HUD_ON)


def _meter_with(**changes: object) -> dict:
    meter = copy.deepcopy(METER)
    for key, value in changes.items():
        meter["display"][key] = value
    return meter


@pytest.mark.parametrize(
    "effects",
    [
        {"moderate_below": "half"},
        {"moderate_below": True},
        {"moderate_below": 25, "critical_below": 50},
        {"intrusive_below": None, "critical_below": "low"},
        {"intrusive_thoughts": "don't turn around"},
        {"intrusive_thoughts": ["ok"] * 9},
        {"intrusive_thoughts": [""]},
        {"intrusive_thoughts": ["x" * 61]},
        {"intrusive_thoughts": [7]},
    ],
)
def test_invalid_meter_effects_are_rejected(effects: dict) -> None:
    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"sanity": _meter_with(effects=effects)}, HUD_ON)


def test_effects_must_be_an_object() -> None:
    with pytest.raises(DisplayHintValidationError, match="object"):
        validate_display_hints({"sanity": _meter_with(effects=[1])}, HUD_ON)


def test_valid_effects_with_thoughts_pass() -> None:
    effects = {
        "moderate_below": 50,
        "critical_below": 50,
        "intrusive_below": 50,
        "intrusive_thoughts": ["x" * 60] * 8,
    }

    validate_display_hints({"sanity": _meter_with(effects=effects)}, HUD_ON)


@pytest.mark.parametrize(
    "bounds",
    [
        {"clamp_min": 100, "clamp_max": 0},
        {"clamp_min": 5, "clamp_max": 5},
        {"clamp_min": "0"},
        {"clamp_max": True},
    ],
)
def test_invalid_meter_clamp_is_rejected(bounds: dict) -> None:
    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"sanity": _meter_with(**bounds)}, HUD_ON)


@pytest.mark.parametrize(
    "glitch",
    [
        {"source": "sanity", "below": "low", "chance": 0.02},
        {"source": "sanity", "below": 25, "chance": 1.5},
        {"source": "sanity", "below": 25, "chance": -0.1},
        {"source": "sanity", "below": 25, "chance": "often"},
    ],
)
def test_invalid_glitch_numbers_are_rejected(glitch: dict) -> None:
    clock = copy.deepcopy(CLOCK)
    clock["display"]["glitch"] = glitch

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints(_schema(shift_minutes=clock, sanity=METER), HUD_ON)


def test_mood_map_keys_must_be_enum_options() -> None:
    field = copy.deepcopy(TIER)
    field["display"]["mood_map"]["panic"] = "combat"

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"tension": field}, HUD_ON)


def test_mood_map_values_must_be_known_moods() -> None:
    field = copy.deepcopy(TIER)
    field["display"]["mood_map"]["uneasy"] = "jazzy"

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"tension": field}, HUD_ON)


def test_track_map_keys_must_be_enum_options() -> None:
    field = copy.deepcopy(TIER)
    field["display"]["track_map"]["panic"] = "night-desk-music/panic.mp3"

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"tension": field}, HUD_ON)


@pytest.mark.parametrize(
    "object_key",
    ["../secret.mp3", "/abs/tense.mp3", "night-desk-music/tense.wav", "", 7, None],
)
def test_track_map_values_must_be_plain_mp3_object_keys(object_key: object) -> None:
    field = copy.deepcopy(TIER)
    field["display"]["track_map"]["tense"] = object_key

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"tension": field}, HUD_ON)


def test_track_map_must_be_an_object() -> None:
    field = copy.deepcopy(TIER)
    field["display"]["track_map"] = ["night-desk-music/tense.mp3"]

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"tension": field}, HUD_ON)


def test_tier_track_keys_reads_the_tier_hint_even_inside_an_object() -> None:
    schema = {"player": {"type": "object", "fields": {"tier": copy.deepcopy(TIER)}}}

    assert tier_track_keys(schema)["dread"] == "night-desk-music/dread.mp3"


def test_tier_track_keys_is_empty_without_a_track_map() -> None:
    field = copy.deepcopy(TIER)
    del field["display"]["track_map"]

    assert tier_track_keys({"tension": field, "sanity": METER}) == {}


def test_resolve_tier_track_urls_builds_public_urls(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "r2_bucket_name", "")
    monkeypatch.setattr(settings, "core_api_public_url", "http://localhost:8000")

    urls = resolve_tier_track_urls({"tension": copy.deepcopy(TIER)})

    assert urls["tense"] == "http://localhost:8000/uploads/night-desk-music/tense.mp3"
    assert set(urls) == {"uneasy", "tense", "dread"}


def test_meter_tiers_must_strictly_descend() -> None:
    field = copy.deepcopy(METER)
    field["display"]["tiers"] = [
        {"name": "a", "min": 50},
        {"name": "b", "min": 50},
        {"name": "c"},
    ]

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"sanity": field}, HUD_ON)


def test_glitch_source_must_be_a_declared_meter() -> None:
    field = copy.deepcopy(CLOCK)
    field["display"]["glitch"]["source"] = "ghost"

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"shift": field, "sanity": METER}, HUD_ON)


def test_glitch_source_must_be_a_meter_not_any_number() -> None:
    schema = _schema(shift=CLOCK, sanity={"type": "number"})

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints(schema, HUD_ON)


@pytest.mark.parametrize("start", ["25:00", "7:5", "noon", "23:60"])
def test_clock_start_must_be_a_valid_time(start: str) -> None:
    field = copy.deepcopy(CLOCK)
    field["display"]["start"] = start
    field["display"].pop("glitch")

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"shift": field}, HUD_ON)


def test_clock_format_must_be_12h_or_24h() -> None:
    field = copy.deepcopy(CLOCK)
    field["display"]["format"] = "military"
    field["display"].pop("glitch")

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"shift": field}, HUD_ON)


def test_a_hidden_field_cannot_carry_a_hint() -> None:
    field = copy.deepcopy(METER)
    field["hidden"] = True

    with pytest.raises(DisplayHintValidationError):
        validate_display_hints({"sanity": field}, HUD_ON)


def test_strip_removes_every_hint_and_keeps_everything_else() -> None:
    stripped = strip_display_hints(_valid())

    assert "display" not in stripped["sanity"]
    assert stripped["sanity"]["max"] == 100
    assert stripped["tension_tier"]["options"] == ["uneasy", "tense", "dread"]


def test_strip_reaches_into_objects_and_does_not_mutate_its_input() -> None:
    schema = {"player": {"type": "object", "fields": {"sanity": copy.deepcopy(METER)}}}

    stripped = strip_display_hints(schema)

    assert "display" not in stripped["player"]["fields"]["sanity"]
    assert "display" in schema["player"]["fields"]["sanity"]


async def _creator(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


async def _enable_hud(db_session, scenario_id, creator, tools=("status_hud",)):
    async def no_rows(tool_key: str, owned_id: uuid.UUID) -> int:
        return 0

    await ToolService(ScenarioRepo(db_session), no_rows).update_tools(
        scenario_id, creator.user_id, ToolsUpdate(enabled_tools=list(tools))
    )


async def test_scenario_update_with_hints_is_gated_on_the_tool(
    db_session: AsyncSession,
) -> None:
    creator = await _creator(db_session)
    service = ScenarioService(ScenarioRepo(db_session))
    scenario = await service.create_scenario(
        creator.user_id,
        ScenarioCreate(title="Night Desk", mode="master", complexity_tier="master"),
    )

    with pytest.raises(ToolNotEnabledError):
        await service.update_scenario(
            scenario.scenario_id,
            creator.user_id,
            ScenarioUpdate(state_schema=_valid()),
        )
    await _enable_hud(db_session, scenario.scenario_id, creator)
    updated = await service.update_scenario(
        scenario.scenario_id, creator.user_id, ScenarioUpdate(state_schema=_valid())
    )

    assert updated.state_schema["sanity"]["display"]["kind"] == "meter"


async def test_scenario_update_rejects_an_invalid_hint(
    db_session: AsyncSession,
) -> None:
    creator = await _creator(db_session)
    service = ScenarioService(ScenarioRepo(db_session))
    scenario = await service.create_scenario(
        creator.user_id,
        ScenarioCreate(title="Night Desk", mode="master", complexity_tier="master"),
    )
    await _enable_hud(db_session, scenario.scenario_id, creator)

    with pytest.raises(DisplayHintValidationError):
        await service.update_scenario(
            scenario.scenario_id,
            creator.user_id,
            ScenarioUpdate(state_schema=_schema(a=CLOCK, b=CLOCK, sanity=METER)),
        )


async def _snapshot_of(db_session, creator, tools) -> dict:
    service = ScenarioService(ScenarioRepo(db_session))
    scenario = await service.create_scenario(
        creator.user_id,
        ScenarioCreate(title="Night Desk", mode="master", complexity_tier="master"),
    )
    await _enable_hud(db_session, scenario.scenario_id, creator, ("status_hud",))
    await service.update_scenario(
        scenario.scenario_id, creator.user_id, ScenarioUpdate(state_schema=_valid())
    )
    await _enable_hud(db_session, scenario.scenario_id, creator, tuple(tools))
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)
    stored.status = "published"
    await db_session.flush()
    result = await _make_service(db_session).create_playthrough(
        user_id=creator.user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )
    pinned = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    return pinned.scenario_snapshot


async def test_snapshot_keeps_hints_when_the_tool_is_on(
    db_session: AsyncSession,
) -> None:
    creator = await _creator(db_session)

    snapshot = await _snapshot_of(db_session, creator, ["status_hud"])

    assert snapshot["state_schema"]["shift_minutes"]["display"]["kind"] == "clock"
    assert snapshot["tier_tracks"]["uneasy"].endswith("/night-desk-music/uneasy.mp3")


async def test_snapshot_strips_hints_when_the_tool_is_off_but_data_is_kept(
    db_session: AsyncSession,
) -> None:
    creator = await _creator(db_session)

    snapshot = await _snapshot_of(db_session, creator, [])

    assert "display" not in snapshot["state_schema"]["sanity"]
    assert snapshot["state_schema"]["sanity"]["max"] == 100
    assert "tier_tracks" not in snapshot


def test_hints_left_over_from_when_the_tool_was_on_do_not_block_other_edits() -> None:
    previous = _valid()
    edited = _valid()
    edited["gold"] = {"type": "number"}

    validate_display_hints(edited, [], previous)


def test_a_changed_hint_is_still_refused_while_the_tool_is_off() -> None:
    previous = _valid()
    edited = _valid()
    edited["sanity"]["display"]["label"] = "Nerves"

    with pytest.raises(ToolNotEnabledError):
        validate_display_hints(edited, [], previous)


def test_a_new_hint_is_refused_while_the_tool_is_off() -> None:
    previous = {"sanity": {"type": "number"}}

    with pytest.raises(ToolNotEnabledError):
        validate_display_hints(_valid(), [], previous)


def test_leftover_hints_are_not_revalidated_while_the_tool_is_off() -> None:
    previous = _schema(a=CLOCK, b=CLOCK, sanity=METER)

    validate_display_hints(copy.deepcopy(previous), [], previous)


async def test_editing_the_schema_after_disabling_the_hud_still_works(
    db_session: AsyncSession,
) -> None:
    creator = await _creator(db_session)
    service = ScenarioService(ScenarioRepo(db_session))
    scenario = await service.create_scenario(
        creator.user_id,
        ScenarioCreate(title="Night Desk", mode="master", complexity_tier="master"),
    )
    await _enable_hud(db_session, scenario.scenario_id, creator)
    await service.update_scenario(
        scenario.scenario_id, creator.user_id, ScenarioUpdate(state_schema=_valid())
    )
    await _enable_hud(db_session, scenario.scenario_id, creator, ())
    edited = _valid()
    edited["gold"] = {"type": "number"}

    updated = await service.update_scenario(
        scenario.scenario_id, creator.user_id, ScenarioUpdate(state_schema=edited)
    )

    assert "gold" in updated.state_schema
    assert updated.state_schema["sanity"]["display"]["kind"] == "meter"
