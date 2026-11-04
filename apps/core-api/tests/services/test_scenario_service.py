"""Unit/integration tests for ScenarioService."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models.entity import Entity
from app.db.models.fact import Fact
from app.db.models.map_connection import MapConnection
from app.db.models.map_pin import MapPin
from app.db.models.scenario_condition import ScenarioCondition
from app.db.models.scenario_entity_type import ScenarioEntityType
from app.db.models.scenario_map import ScenarioMap
from app.db.models.scenario_minigame import ScenarioMinigame
from app.db.models.user import User
from app.exceptions.memory_exceptions import MemoryPurgeError
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.models.scenario import ScenarioCreate, ScenarioUpdate
from app.repositories.condition_repo import ConditionRepo
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.map_repo import MapRepo
from app.repositories.minigame_repo import MinigameRepo
from app.repositories.scenario_entity_type_repo import ScenarioEntityTypeRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from app.services.scenario_service import ScenarioService
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.usefixtures("scenario_memory_purge")


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Fixture creating a test user."""
    user_repo = UserRepo(db_session)
    return await user_repo.create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator User"
    )


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Fixture creating a secondary test user."""
    user_repo = UserRepo(db_session)
    return await user_repo.create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Other User"
    )


@pytest.mark.asyncio
async def test_create_scenario(db_session: AsyncSession, sample_user: User):
    service = ScenarioService(ScenarioRepo(db_session))
    payload = ScenarioCreate(
        title="Dungeon Escape",
        mode="newbie",
        complexity_tier="newbie",
        logline="Escape the dark dungeon",
    )
    result = await service.create_scenario(sample_user.user_id, payload)

    assert result.title == "Dungeon Escape"
    assert result.mode == "newbie"
    assert result.status == "draft"
    assert result.current_version == 1
    assert result.creator_id == sample_user.user_id


@pytest.mark.asyncio
async def test_get_draft_scenario_access_control(
    db_session: AsyncSession, sample_user: User, other_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))
    payload = ScenarioCreate(
        title="Secret Draft", mode="master", complexity_tier="master"
    )
    created = await service.create_scenario(sample_user.user_id, payload)

    # Creator gets scenario
    scen = await service.get_scenario(created.scenario_id, sample_user.user_id)
    assert scen.scenario_id == created.scenario_id

    # Non-creator gets 404
    with pytest.raises(ScenarioNotFoundError):
        await service.get_scenario(created.scenario_id, other_user.user_id)

    # Unauthenticated gets 404
    with pytest.raises(ScenarioNotFoundError):
        await service.get_scenario(created.scenario_id, None)


@pytest.mark.asyncio
async def test_update_scenario_selective_version_increment(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))
    created = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(title="Initial Title", mode="newbie", complexity_tier="newbie"),
    )
    assert created.current_version == 1

    # Metadata update does NOT increment version
    updated1 = await service.update_scenario(
        created.scenario_id,
        sample_user.user_id,
        ScenarioUpdate(title="Updated Title"),
    )
    assert updated1.title == "Updated Title"
    assert updated1.current_version == 1

    # Story field update DOES increment version
    updated2 = await service.update_scenario(
        created.scenario_id,
        sample_user.user_id,
        ScenarioUpdate(narrator_persona="Dark Narrator Persona"),
    )
    assert updated2.narrator_persona == "Dark Narrator Persona"
    assert updated2.current_version == 2


@pytest.mark.asyncio
async def test_delete_scenario_hard_vs_soft(
    db_session: AsyncSession, sample_user: User
):
    repo = ScenarioRepo(db_session)
    service = ScenarioService(repo)
    created = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(title="Unplayed", mode="newbie", complexity_tier="newbie"),
    )

    # Hard delete scenario with 0 playthroughs
    await service.delete_scenario(created.scenario_id, sample_user.user_id)
    with pytest.raises(ScenarioNotFoundError):
        await service.get_scenario(created.scenario_id, sample_user.user_id)


@pytest.mark.asyncio
async def test_hard_delete_purges_the_scenario_memory_first(
    db_session: AsyncSession, sample_user: User, scenario_memory_purge
):
    service = ScenarioService(ScenarioRepo(db_session))
    created = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(title="Unplayed", mode="newbie", complexity_tier="newbie"),
    )

    await service.delete_scenario(created.scenario_id, sample_user.user_id)

    scenario_memory_purge.assert_awaited_once_with(scenario_ids=[created.scenario_id])


@pytest.mark.asyncio
async def test_hard_delete_survives_a_memory_purge_failure(
    db_session: AsyncSession, sample_user: User, scenario_memory_purge
):
    scenario_memory_purge.side_effect = MemoryPurgeError("unavailable")
    service = ScenarioService(ScenarioRepo(db_session))
    created = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(title="Unplayed", mode="newbie", complexity_tier="newbie"),
    )

    await service.delete_scenario(created.scenario_id, sample_user.user_id)

    with pytest.raises(ScenarioNotFoundError):
        await service.get_scenario(created.scenario_id, sample_user.user_id)


@pytest.mark.asyncio
async def test_archiving_a_scenario_makes_no_memory_call(
    db_session: AsyncSession, sample_user: User, scenario_memory_purge
):
    repo = ScenarioRepo(db_session)
    service = ScenarioService(repo)
    created = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(title="Played", mode="newbie", complexity_tier="newbie"),
    )
    scenario = await repo.get_by_id(created.scenario_id)
    scenario.published_at = datetime.now(UTC)
    await repo.update(scenario)

    await service.delete_scenario(created.scenario_id, sample_user.user_id)

    scenario_memory_purge.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_scenarios_mine_requires_user(db_session: AsyncSession):
    service = ScenarioService(ScenarioRepo(db_session))
    with pytest.raises(ScenarioAccessDeniedError):
        await service.list_scenarios(current_user_id=None, mine=True)


async def _seed_test_map_and_pins(
    db_session: AsyncSession,
    scenario_id: uuid.UUID,
    loc1_id: uuid.UUID,
    loc2_id: uuid.UUID,
) -> uuid.UUID:
    map_repo = MapRepo(db_session)
    smap = await map_repo.create_map(
        ScenarioMap(scenario_id=scenario_id, name="Citadel Map", display_order=0)
    )
    await map_repo.create_pin(
        MapPin(
            map_id=smap.map_id,
            scenario_id=scenario_id,
            entity_id=loc1_id,
            x=0.1,
            y=0.2,
            is_start_location=True,
        )
    )
    await map_repo.create_pin(
        MapPin(
            map_id=smap.map_id,
            scenario_id=scenario_id,
            entity_id=loc2_id,
            x=0.8,
            y=0.9,
            is_start_location=False,
        )
    )
    pair = sorted((loc1_id, loc2_id))
    await map_repo.create_connection(
        MapConnection(
            scenario_id=scenario_id,
            entity_id_a=pair[0],
            entity_id_b=pair[1],
            label="Main Highway",
        )
    )
    return smap.map_id


async def _seed_test_world(
    db_session: AsyncSession, scenario_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    et_repo = ScenarioEntityTypeRepo(db_session)
    await et_repo.create(
        ScenarioEntityType(
            scenario_id=scenario_id,
            type_key="relic",
            display_label="Relic",
            attributes_schema={},
        )
    )
    entity_repo = EntityRepo(db_session)
    loc1 = await entity_repo.create(
        Entity(
            scenario_id=scenario_id,
            entity_type="location",
            canonical_name="North Gate",
        )
    )
    loc2 = await entity_repo.create(
        Entity(
            scenario_id=scenario_id,
            entity_type="location",
            canonical_name="South Gate",
        )
    )
    minigame_repo = MinigameRepo(db_session)
    await minigame_repo.create(
        ScenarioMinigame(
            scenario_id=scenario_id,
            label="Defense",
            minigame_type="dodge",
            outcome_mode="binary",
            dodge_config={"difficulty": 2},
            win_mutation={"path": "player.health", "op": "set", "value": 100},
            lose_mutation={"path": "player.health", "op": "decrement", "value": 20},
        )
    )
    return loc1.entity_id, loc2.entity_id


@pytest.mark.asyncio
async def test_duplicate_master_scenario_sub_resources(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))
    source = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(title="Citadel", mode="master", complexity_tier="master"),
    )
    loc1_id, loc2_id = await _seed_test_world(db_session, source.scenario_id)
    await _seed_test_map_and_pins(db_session, source.scenario_id, loc1_id, loc2_id)

    dup = await service.duplicate_scenario(source.scenario_id, sample_user.user_id)
    assert dup.title == "Citadel (Copy)"

    dup_ets = await ScenarioEntityTypeRepo(db_session).list_by_scenario(dup.scenario_id)
    assert len(dup_ets) == 1 and dup_ets[0].type_key == "relic"

    dup_entities = await EntityRepo(db_session).list_by_scenario(dup.scenario_id)
    assert len(dup_entities) == 2

    dup_maps = await MapRepo(db_session).list_maps_by_scenario(dup.scenario_id)
    assert len(dup_maps) == 1 and dup_maps[0].name == "Citadel Map"

    dup_pins = await MapRepo(db_session).list_pins_by_scenario(dup.scenario_id)
    assert len(dup_pins) == 2 and sum(1 for p in dup_pins if p.is_start_location) == 1

    dup_conns = await MapRepo(db_session).list_connections_by_scenario(dup.scenario_id)
    assert len(dup_conns) == 1 and dup_conns[0].entity_id_a < dup_conns[0].entity_id_b

    dup_games = await MinigameRepo(db_session).list_by_scenario(dup.scenario_id)
    assert len(dup_games) == 1 and dup_games[0].label == "Defense"


@pytest.mark.asyncio
async def test_duplicate_preserves_condition_evaluation_order(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))
    source = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(title="Ordered", mode="master", complexity_tier="master"),
    )
    base = datetime(2026, 10, 26, tzinfo=UTC)
    repo = ConditionRepo(db_session)
    await repo.create_all(
        [
            ScenarioCondition(
                scenario_id=source.scenario_id,
                label=label,
                narrator_instruction="",
                created_at=base + timedelta(seconds=offset),
            )
            for label, offset in (("third", 3), ("first", 1), ("second", 2))
        ]
    )

    dup = await service.duplicate_scenario(source.scenario_id, sample_user.user_id)

    copied = await repo.list_by_scenario(dup.scenario_id)
    assert [condition.label for condition in copied] == ["first", "second", "third"]


def _document(*blocks: tuple[str, str | None, str]) -> dict[str, object]:
    return {
        "blocks": [
            {"kind": kind, "label": label, "text": text} for kind, label, text in blocks
        ]
    }


@pytest.mark.asyncio
async def test_new_story_defaults_to_private_newbie(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))

    created = await service.create_scenario(
        sample_user.user_id, ScenarioCreate(title="The Door Below")
    )

    assert created.visibility == "private"
    assert created.mode == "newbie"
    assert created.mood_tags == []
    assert created.player_mode == "written"
    assert created.guide_seen_features == []
    assert created.narrator_persona_document is None


@pytest.mark.asyncio
async def test_create_renders_documents_into_plain_text_fields(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))

    created = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(
            title="The Door Below",
            world_data={
                "premiseDocument": _document(
                    ("text", None, "A keeper finds a door."),
                    ("answer", "Stakes", "The tide is rising."),
                ),
                "worldLoreDocument": _document(("text", None, "Salt and rust.")),
                "openingDocument": _document(("text", None, "You wake on the rocks.")),
                "alwaysRemember": ["The lamp never goes out."],
            },
            narrator_persona_document=_document(("text", None, "Dry and slow.")),
        ),
    )

    assert created.world_data["premise"] == (
        "A keeper finds a door.\n\nStakes: The tide is rising."
    )
    assert created.world_data["worldLore"] == "Salt and rust."
    assert created.world_data["alwaysRemember"] == ["The lamp never goes out."]
    assert created.opening_scene == "You wake on the rocks."
    assert created.narrator_persona == "Dry and slow."
    assert created.narrator_persona_document is not None


@pytest.mark.asyncio
async def test_update_rerenders_documents_and_clearing_the_opening_empties_it(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))
    created = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(
            title="The Door Below",
            world_data={"openingDocument": _document(("text", None, "First"))},
        ),
    )

    updated = await service.update_scenario(
        created.scenario_id,
        sample_user.user_id,
        ScenarioUpdate(
            world_data={"openingDocument": _document(("text", None, "  "))},
            narrator_persona_document=_document(("text", None, "Poetic")),
        ),
    )

    assert updated.opening_scene is None
    assert updated.narrator_persona == "Poetic"


@pytest.mark.asyncio
async def test_story_documents_and_mood_bump_the_version_but_seen_features_do_not(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))
    created = await service.create_scenario(
        sample_user.user_id, ScenarioCreate(title="The Door Below")
    )
    row = await ScenarioRepo(db_session).get_by_id(created.scenario_id)
    edited_before = row.content_edited_at

    seen = await service.update_scenario(
        created.scenario_id,
        sample_user.user_id,
        ScenarioUpdate(guide_seen_features=["triggers"]),
    )
    await db_session.refresh(row)
    assert seen.guide_seen_features == ["triggers"]
    assert seen.current_version == 1
    assert row.content_edited_at == edited_before

    moody = await service.update_scenario(
        created.scenario_id,
        sample_user.user_id,
        ScenarioUpdate(mood_tags=["eerie", "tense"], player_mode="player_created"),
    )
    assert moody.current_version == 2
    assert moody.mood_tags == ["eerie", "tense"]
    assert moody.player_mode == "player_created"


@pytest.mark.parametrize(
    "always_remember",
    [["x"] * 31, ["y" * 301], "not a list", [1, 2]],
)
def test_always_remember_limits_are_validated(always_remember):
    with pytest.raises(ValueError):
        ScenarioCreate(title="T", world_data={"alwaysRemember": always_remember})


def test_always_remember_at_the_limits_is_accepted():
    payload = ScenarioCreate(title="T", world_data={"alwaysRemember": ["y" * 300] * 30})

    assert len(payload.world_data["alwaysRemember"]) == 30


@pytest.mark.asyncio
async def test_duplicate_copies_guided_fields_cards_and_links_for_newbie(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))
    source = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(
            title="The Door Below",
            mood_tags=["eerie"],
            player_mode="player_created",
            narrator_persona_document=_document(("text", None, "Dry.")),
        ),
    )
    await service.update_scenario(
        source.scenario_id,
        sample_user.user_id,
        ScenarioUpdate(guide_seen_features=["triggers"]),
    )
    entity_repo = EntityRepo(db_session)
    mara = await entity_repo.create(
        Entity(
            scenario_id=source.scenario_id,
            entity_type="character",
            canonical_name="Mara",
            aliases=["Mara"],
            description="The keeper.",
            lore_document=_document(("text", None, "The keeper.")),
            is_player=True,
        )
    )
    lighthouse = await entity_repo.create(
        Entity(
            scenario_id=source.scenario_id,
            entity_type="location",
            canonical_name="The Lighthouse",
        )
    )
    await FactRepo(db_session).create(
        Fact(
            scenario_id=source.scenario_id,
            subject_entity_id=mara.entity_id,
            predicate="lives in",
            object_entity_id=lighthouse.entity_id,
        )
    )

    await service.update_scenario(
        source.scenario_id,
        sample_user.user_id,
        ScenarioUpdate(
            rules={
                "portrait_opening_ids": [str(mara.entity_id)],
                "portrait_schedule": [
                    {"turn": 2, "character_ids": [str(mara.entity_id)]}
                ],
            }
        ),
    )

    copy = await service.duplicate_scenario(source.scenario_id, sample_user.user_id)

    assert copy.mood_tags == ["eerie"]
    assert copy.player_mode == "player_created"
    assert copy.narrator_persona_document is not None
    assert copy.guide_seen_features == []
    copied_entities = await entity_repo.list_by_scenario(copy.scenario_id)
    copied_mara = next(e for e in copied_entities if e.canonical_name == "Mara")
    assert copy.rules["portrait_opening_ids"] == [str(copied_mara.entity_id)]
    assert copy.rules["portrait_schedule"] == [
        {"turn": 2, "character_ids": [str(copied_mara.entity_id)]}
    ]
    assert copied_mara.is_player is True
    assert copied_mara.lore_document is not None
    copied_facts = await FactRepo(db_session).list_by_scenario(copy.scenario_id)
    assert [f.predicate for f in copied_facts] == ["lives in"]
    assert copied_facts[0].subject_entity_id == copied_mara.entity_id


@pytest.mark.asyncio
async def test_strategy_scenario_persists_canonical_document(
    db_session: AsyncSession, sample_user: User
):
    service = ScenarioService(ScenarioRepo(db_session))
    created = await service.create_scenario(
        sample_user.user_id,
        ScenarioCreate(
            title="Border Kingdoms",
            mode="strategy",
            complexity_tier="master",
            strategy_document={"schema_version": 1},
        ),
    )

    assert created.mode == "strategy"
    assert created.strategy_document["schema_version"] == 1
    assert "tuning" in created.strategy_document


def test_strategy_mode_requires_a_document():
    with pytest.raises(ValueError, match="strategy_document is required"):
        ScenarioCreate(title="Border Kingdoms", mode="strategy")


def test_non_strategy_mode_rejects_a_strategy_document():
    with pytest.raises(ValueError, match="only valid for strategy mode"):
        ScenarioCreate(
            title="Border Kingdoms",
            mode="newbie",
            strategy_document={"schema_version": 1},
        )
