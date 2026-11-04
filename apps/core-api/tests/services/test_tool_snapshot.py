"""Snapshot pinning, contributors and copy behaviour for optional tools."""

import uuid

import pytest
from app.db.models.scenario import Scenario
from app.models.playthrough import PlaythroughCreate
from app.models.tools import ToolsUpdate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.end_condition_repo import EndConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.invariant_repo import InvariantRepo
from app.repositories.map_repo import MapRepo
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.minigame_repo import MinigameRepo
from app.repositories.participant_repo import ParticipantRepo
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.scenario_music_repo import ScenarioMusicRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.share_repo import ShareRepo
from app.repositories.turn_log_repo import TurnLogRepo
from app.repositories.user_repo import UserRepo
from app.services.playthrough_service import PlaythroughService
from app.services.scenario_service import ScenarioService
from app.services.tool_service import ToolService
from app.tools import registry
from sqlalchemy.ext.asyncio import AsyncSession

NO_TOOLS_MASTER_SNAPSHOT_KEYS = {
    "mode",
    "narrator_persona",
    "world_data",
    "setup_schema",
    "state_schema",
    "checkpoints",
    "narration_font",
    "narrator_voice_name",
    "music_tracks",
    "action_chips",
    "entities",
    "facts",
    "scenario_conditions",
    "rule_invariants",
    "end_conditions",
    "scenario_minigames",
}


def _make_service(db_session: AsyncSession) -> PlaythroughService:
    return PlaythroughService(
        playthrough_repo=PlaythroughRepo(db_session),
        participant_repo=ParticipantRepo(db_session),
        scenario_repo=ScenarioRepo(db_session),
        share_repo=ShareRepo(db_session),
        turn_log_repo=TurnLogRepo(db_session),
        entity_repo=EntityRepo(db_session),
        fact_repo=FactRepo(db_session),
        condition_repo=ConditionRepo(db_session),
        invariant_repo=InvariantRepo(db_session),
        end_condition_repo=EndConditionRepo(db_session),
        map_repo=MapRepo(db_session),
        minigame_repo=MinigameRepo(db_session),
        scenario_music_repo=ScenarioMusicRepo(db_session),
        memory_outbox_repo=MemoryOutboxRepo(db_session),
        user_repo=UserRepo(db_session),
    )


async def _publish_master_scenario(
    db_session: AsyncSession, enabled_tools: list[str]
) -> tuple[uuid.UUID, Scenario]:
    user = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev User"
    )
    scenario = Scenario(
        creator_id=user.user_id,
        title="Night Desk",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
        enabled_tools=enabled_tools,
    )
    db_session.add(scenario)
    await db_session.flush()
    return user.user_id, scenario


async def _start(db_session: AsyncSession, user_id: uuid.UUID, scenario: Scenario):
    return await _make_service(db_session).create_playthrough(
        user_id=user_id,
        data=PlaythroughCreate(scenario_id=scenario.scenario_id, setup_values={}),
    )


@pytest.fixture
def fake_contributor():
    registry.register_snapshot_contributor(
        "composure", lambda scenario, rows: {"composure_marker": scenario.title}
    )
    yield
    registry.unregister_snapshot_contributor("composure")


async def test_snapshot_pins_enabled_tools(db_session: AsyncSession):
    user_id, scenario = await _publish_master_scenario(db_session, ["rule_checks"])

    result = await _start(db_session, user_id, scenario)

    assert result.scenario_snapshot["enabled_tools"] == ["rule_checks"]


async def test_later_tool_change_does_not_alter_running_playthrough(
    db_session: AsyncSession,
):
    user_id, scenario = await _publish_master_scenario(db_session, ["rule_checks"])
    result = await _start(db_session, user_id, scenario)

    async def no_rows(tool_key: str, scenario_id: uuid.UUID) -> int:
        return 0

    await ToolService(ScenarioRepo(db_session), no_rows).update_tools(
        scenario.scenario_id, user_id, ToolsUpdate(enabled_tools=["composure"])
    )
    reread = await _make_service(db_session).get_playthrough(
        result.playthrough_id, user_id
    )

    assert reread.scenario_snapshot["enabled_tools"] == ["rule_checks"]


async def test_enabled_tool_contributor_is_merged_into_snapshot(
    db_session: AsyncSession, fake_contributor
):
    user_id, scenario = await _publish_master_scenario(db_session, ["composure"])

    result = await _start(db_session, user_id, scenario)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)

    assert stored.scenario_snapshot["composure_marker"] == "Night Desk"


async def test_disabled_tool_contributes_nothing(
    db_session: AsyncSession, fake_contributor
):
    user_id, scenario = await _publish_master_scenario(db_session, [])

    result = await _start(db_session, user_id, scenario)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)

    assert "composure_marker" not in stored.scenario_snapshot


async def test_no_tools_master_snapshot_matches_pre_change_shape(
    db_session: AsyncSession,
):
    user_id, scenario = await _publish_master_scenario(db_session, [])

    result = await _start(db_session, user_id, scenario)
    stored = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)

    assert set(stored.scenario_snapshot) == NO_TOOLS_MASTER_SNAPSHOT_KEYS | {
        "enabled_tools",
        "visibility",
        "opening_scene",
        "mood_tags",
        "genre_tags",
        "strategy_document",
        "character_avatar_assets",
    }
    assert stored.scenario_snapshot["enabled_tools"] == []


async def test_duplicate_preserves_enabled_tools(db_session: AsyncSession):
    user_id, scenario = await _publish_master_scenario(
        db_session, ["status_hud", "atmosphere"]
    )

    copy = await ScenarioService(ScenarioRepo(db_session)).duplicate_scenario(
        scenario.scenario_id, user_id
    )

    assert copy.enabled_tools == ["status_hud", "atmosphere"]


async def _pinned_snapshot(
    db_session: AsyncSession, user_id: uuid.UUID, scenario: Scenario
) -> dict[str, object]:
    result = await _start(db_session, user_id, scenario)
    playthrough = await PlaythroughRepo(db_session).get_by_id(result.playthrough_id)
    assert playthrough is not None
    return playthrough.scenario_snapshot


async def test_snapshot_pins_a_valid_narration_output_limit(db_session: AsyncSession):
    user_id, scenario = await _publish_master_scenario(db_session, [])
    scenario.rules = {"narration_max_output_tokens": 1500}
    await db_session.flush()

    snapshot = await _pinned_snapshot(db_session, user_id, scenario)

    assert snapshot["narration_max_output_tokens"] == 1500


async def test_snapshot_omits_the_narration_limit_when_unset_or_invalid(
    db_session: AsyncSession,
):
    user_id, scenario = await _publish_master_scenario(db_session, [])
    unset = await _pinned_snapshot(db_session, user_id, scenario)
    scenario.rules = {"narration_max_output_tokens": 999999}
    await db_session.flush()
    invalid = await _pinned_snapshot(db_session, user_id, scenario)

    assert "narration_max_output_tokens" not in unset
    assert "narration_max_output_tokens" not in invalid


async def test_narration_limit_is_not_sent_to_the_client(db_session: AsyncSession):
    user_id, scenario = await _publish_master_scenario(db_session, [])
    scenario.rules = {"narration_max_output_tokens": 1500}
    await db_session.flush()

    result = await _start(db_session, user_id, scenario)

    assert "narration_max_output_tokens" not in result.scenario_snapshot


async def test_snapshot_pins_the_intent_marker_group_only_when_it_is_a_schema_group(
    db_session: AsyncSession,
):
    user_id, scenario = await _publish_master_scenario(db_session, [])
    scenario.state_schema = {"intent": {"type": "object", "fields": {}}}
    scenario.rules = {"intent_marker_group": "intent"}
    await db_session.flush()
    valid = await _pinned_snapshot(db_session, user_id, scenario)
    scenario.rules = {"intent_marker_group": "nope"}
    await db_session.flush()
    invalid = await _pinned_snapshot(db_session, user_id, scenario)

    assert valid["intent_marker_group"] == "intent"
    assert "intent_marker_group" not in invalid
